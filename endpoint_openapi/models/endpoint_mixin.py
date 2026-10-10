# Copyright 2026 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models


class EndpointMixin(models.AbstractModel):
    """Describe endpoints for OpenAPI docs via `openapi.doc.mixin`."""

    _name = "endpoint.mixin"
    _inherit = ["endpoint.mixin", "openapi.doc.mixin"]

    def _openapi_route_info(self):
        """Use the routing of the endpoint (route, method, auth)."""
        route, routing, __ = self._get_routing_info()
        return route, routing

    def _openapi_api_doc(self):
        """Use the request content type of the endpoint for the request body."""
        api_doc = super()._openapi_api_doc()
        if self.request_content_type:
            api_doc["content_type"] = self.request_content_type
        return api_doc
