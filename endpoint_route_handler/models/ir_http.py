# Copyright 2021 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import logging
from itertools import chain

import werkzeug

from odoo import http, models, tools

from ..registry import EndpointRegistry

_logger = logging.getLogger(__name__)


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _endpoint_route_registry(cls, env):
        return EndpointRegistry.registry_for(env.cr)

    def _generate_routing_rules(self, modules, converters):
        # Override to inject custom endpoint rules.
        return chain(
            super()._generate_routing_rules(modules, converters),
            self._endpoint_routing_rules(),
        )

    @classmethod
    def _endpoint_routing_rules(cls):
        """Yield custom endpoint rules"""
        e_registry = cls._endpoint_route_registry(http.request.env)
        for endpoint_rule in e_registry.get_rules():
            _logger.debug("LOADING %s", endpoint_rule)
            endpoint = endpoint_rule.endpoint
            for url in endpoint_rule.routing["routes"]:
                yield (url, endpoint)

    @tools.ormcache("key", "self._endpoint_route_last_version()", cache="routing")
    def routing_map(self, key=None):
        res = super().routing_map(key=key)
        return res

    # Sentinel stored in the request `__dict__` to memoize the version.
    _endpoint_route_version_attr = "_endpoint_route_last_version"

    @classmethod
    def _endpoint_route_last_version(cls):
        # This is part of the `routing_map` ormcache key, so it runs on
        # every routing map access (e.g. once per `url_for` while rendering
        # a website page). The version only changes when routes are
        # (un)registered, which resets the memo via
        # `_endpoint_route_reset_last_version`. Memoize it on the request
        # object to avoid one SQL round-trip per call.
        # NB: use `__dict__` rather than `getattr`: on a mocked request
        # `getattr` would auto-create a child mock instead of falling back
        # to the default, defeating the memoization.
        # NB: `http.request` is a werkzeug `LocalProxy`; when no request is
        # bound it is falsy (but not `None`), hence the truthiness check.
        request = http.request
        if not request:
            return cls._get_routing_map_last_version(http.request.env)
        version = request.__dict__.get(cls._endpoint_route_version_attr)
        if version is None:
            version = cls._get_routing_map_last_version(request.env)
            request.__dict__[cls._endpoint_route_version_attr] = version
        return version

    @classmethod
    def _endpoint_route_reset_last_version(cls):
        """Drop the memoized version so the next access reads it afresh.

        Must be called whenever routes are (un)registered within a request,
        as the version changes and any value memoized earlier is now stale.
        """
        # `http.request` is a werkzeug `LocalProxy`: falsy (but not `None`)
        # when no request is bound, e.g. when (un)registering routes outside
        # of an HTTP request (tests, crons, module install).
        request = http.request
        if request:
            request.__dict__.pop(cls._endpoint_route_version_attr, None)

    @classmethod
    def _get_routing_map_last_version(cls, env):
        return cls._endpoint_route_registry(env).last_version()

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
