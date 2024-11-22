# Copyright 2021 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import logging

import werkzeug

from odoo import http, models

from ..registry import EndpointRegistry

_logger = logging.getLogger(__name__)


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _endpoint_route_registry(cls, cr):
        return EndpointRegistry.registry_for(cr)

    @classmethod
    def _endpoint_routing_rules(cls):
        """Yield custom endpoint rules"""
        e_registry = cls._endpoint_route_registry(http.request.env.cr)
        for endpoint_rule in e_registry.get_rules():
            _logger.debug("LOADING %s", endpoint_rule)
            endpoint = endpoint_rule.endpoint
            for url in endpoint_rule.routing["routes"]:
                yield url, endpoint, endpoint_rule.routing

    @classmethod
    def routing_map(cls):
        last_version = cls._get_routing_map_last_version(http.request.env.cr)
        if not hasattr(cls, "_routing_map"):
            _logger.debug(
                "routing map just initialized, store last update for this env"
            )
            # routing map just initialized, store last update for this env
            cls._endpoint_route_last_version = last_version
        elif cls._endpoint_route_last_version < last_version:
            _logger.info("Endpoint registry updated, reset routing map")
            cls._endpoint_route_last_version = last_version
        res = super().routing_map()
        # Inject custom endpoint rules
        for url, endpoint, routing in cls._endpoint_routing_rules():
            xtra_keys = (
                'defaults subdomain build_only strict_slashes redirect_to alias host'
            ).split()
            kw = {k: routing[k] for k in xtra_keys if k in routing}
            rule = werkzeug.routing.Rule(
                url,
                endpoint=endpoint,
                methods=routing['methods'],
                **kw
            )
            rule.merge_slashes = False
            res.add(rule)
        return res

    @classmethod
    def _get_routing_map_last_version(cls, cr):
        return cls._endpoint_route_registry(cr).last_version()

    @classmethod
    def _clear_routing_map(cls):
        super()._clear_routing_map()
        if hasattr(cls, "_endpoint_route_last_version"):
            cls._endpoint_route_last_version = 0

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
        except http.SessionExpiredException:
            raise werkzeug.exceptions.Unauthorized()
