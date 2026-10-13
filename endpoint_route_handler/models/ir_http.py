# Copyright 2021 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import logging

import werkzeug

from odoo import http, models, tools

from ..registry import EndpointRegistry
from ..utils import RouteConflictTracker, controller_owner, rule_owner

_logger = logging.getLogger(__name__)


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def _endpoint_route_registry(self, cr=None):
        return EndpointRegistry.registry_for(cr or self.env.cr)

    def _generate_routing_rules(self, modules, converters):
        """Inject custom endpoint rules, skipping the conflicting ones.

        Standard controllers come first and are only tracked.
        Each custom rule is checked against everything tracked so far
        (see `RouteConflictTracker`): the 1st rule wins, as in werkzeug,
        conflicting ones are logged and skipped.

        Cost: one dict lookup per rule (index by URL), negligible compared
        to the build of the routing map (~3 ms for ~800 rules).
        """
        tracker = RouteConflictTracker()
        for url, endpoint in super()._generate_routing_rules(modules, converters):
            # Standard controllers are not checked against each other
            tracker.add(url, endpoint, controller_owner(endpoint))
            yield url, endpoint
        for endpoint_rule, url, endpoint in self._endpoint_routing_rules():
            owner = rule_owner(endpoint_rule)
            conflict = tracker.conflict(url, endpoint)
            if conflict:
                _logger.error(
                    "Route %s %s of %s conflicts w/ %s: skipped",
                    url,
                    tracker.methods_label(endpoint),
                    owner,
                    conflict,
                )
                continue
            tracker.add(url, endpoint, owner)
            yield url, endpoint

    def _endpoint_routing_rules(self):
        """Yield `(endpoint rule, url, endpoint)` for all the custom endpoint rules."""
        e_registry = self._endpoint_route_registry()
        for endpoint_rule in e_registry.get_rules():
            _logger.debug("LOADING %s", endpoint_rule)
            if not endpoint_rule.is_generator:
                for url, endpoint in endpoint_rule.iter_routing_rules(self.env):
                    yield endpoint_rule, url, endpoint
                continue
            # A broken generator must not break the whole routing map.
            # Collect its rules first, so that nothing is yielded on failure.
            try:
                rules = list(endpoint_rule.iter_routing_rules(self.env))
            except Exception:
                _logger.exception("Routes generation failed for %s", endpoint_rule)
                continue
            for url, endpoint in rules:
                yield endpoint_rule, url, endpoint

    @tools.ormcache("key", "cls._endpoint_route_last_version()", cache="routing")
    def routing_map(cls, key=None):
        res = super().routing_map(key=key)
        return res

    def _endpoint_route_last_version(self):
        return self._get_routing_map_last_version()

    def _get_routing_map_last_version(self):
        return self._endpoint_route_registry().last_version()

    @classmethod
    def _auth_method_user_endpoint(cls):
        """Special method for user auth which raises Unauthorized when needed.

        If you get an HTTP request (instead of a JSON one),
        the standard `user` method raises `SessionExpiredException`
        when there's no user session.
        This leads to a redirect to `/web/login`
        which is not desiderable for technical endpoints.

        This method makes sure that no matter the type of request we get,
        a proper exception is raised.
        """
        try:
            cls._auth_method_user()
        except http.SessionExpiredException as err:
            raise werkzeug.exceptions.Unauthorized() from err
