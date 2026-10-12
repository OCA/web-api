# Copyright 2021 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import logging
from itertools import chain

import werkzeug

import odoo
from odoo import api, http, models
from odoo.http.session import SessionExpiredException

from ..registry import EndpointRegistry

_logger = logging.getLogger(__name__)


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _endpoint_route_registry(cls, env):
        return EndpointRegistry.registry_for(env.cr)

    def _generate_routing_rules(self, modules, converters):
        self.__class__._last_env = self.env
        # Override to inject custom endpoint rules.
        return chain(
            super()._generate_routing_rules(modules, converters),
            self._endpoint_routing_rules(),
        )

    @classmethod
    def _endpoint_routing_rules(cls):
        """Yield custom endpoint rules"""
        e_registry = cls._endpoint_route_registry(
            http.request.env
            if (http.request and hasattr(http.request, "env") and http.request.env)
            else (cls._cr_env if hasattr(cls, "_cr_env") else None)
        )
        for endpoint_rule in e_registry.get_rules():
            _logger.debug("LOADING %s", endpoint_rule)
            endpoint = endpoint_rule.endpoint
            for url in endpoint_rule.routing["routes"]:
                yield (url, endpoint)

    @api.ormcache("key", "self._endpoint_route_last_version()", cache="routing")
    def routing_map(self, key=None):
        _logger.info("Generating endpoint routing map for key %s", key)
        registry = self.env.registry
        installed = registry._init_modules.union(
            odoo.tools.config["server_wide_modules"]
        )
        mods = sorted(installed)
        routing_map = werkzeug.routing.Map(
            strict_slashes=False, converters=self._get_converters()
        )
        for url, endpoint in self._generate_routing_rules(
            mods, converters=self._get_converters()
        ):
            from odoo.http.routing_map import ROUTING_KEYS
            from odoo.tools.misc import submap

            from odoo.addons.base.models.ir_http import FasterRule

            routing = submap(endpoint.routing, ROUTING_KEYS)
            if routing["methods"] is not None and "OPTIONS" not in routing["methods"]:
                routing["methods"] = [*routing["methods"], "OPTIONS"]
            rule = FasterRule(url, endpoint=endpoint, **routing)
            rule.merge_slashes = False
            routing_map.add(rule)
        return routing_map

    def _endpoint_route_last_version(self):
        env = (
            http.request.env
            if (http.request and hasattr(http.request, "env") and http.request.env)
            else self.env
        )
        return self._get_routing_map_last_version(env)

    @classmethod
    def _get_routing_map_last_version(cls, env):
        return cls._endpoint_route_registry(env).last_version()

    @classmethod
    def _auth_method_user_endpoint(cls, routing=None):
        """Special method for user auth which raises Unauthorized when needed."""
        try:
            if routing is not None:
                cls._auth_method_user(routing)
            else:
                cls._auth_method_user({"auth": "user"})
        except SessionExpiredException as err:
            raise werkzeug.exceptions.Unauthorized() from err
