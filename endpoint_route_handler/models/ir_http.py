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

    @tools.ormcache("key", "cls._endpoint_route_last_version()", cache="routing")
    def routing_map(cls, key=None):
        res = super().routing_map(key=key)
        return res

    @classmethod
    def _endpoint_route_last_version(cls):
        res = cls._get_routing_map_last_version(http.request.env)
        return res

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
