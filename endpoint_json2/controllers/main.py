# Copyright 2026 Quartile (https://www.quartile.co)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request


class EndpointJson2DocController(http.Controller):
    def _get_accessible_endpoints(self, extra_domain=None):
        domain = [("exec_mode", "=", "json2")] + (extra_domain or [])
        all_endpoints = request.env["endpoint.endpoint"].sudo().search(domain)
        user = request.env.user
        return all_endpoints.filtered(
            lambda ep: ep.json2_group_ids & user.all_group_ids
        )

    def _endpoint_to_doc(self, endpoint):
        return {
            "name": endpoint.name,
            "description": endpoint.json2_description or "",
            "method": endpoint.json2_method,
            "model": endpoint.json2_model_name,
            "url": endpoint.route,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.param_type,
                    "required": p.required,
                    "description": p.description or "",
                    "default": p.default_value,
                }
                for p in endpoint.json2_param_ids
            ],
        }

    @http.route(
        "/json2/doc",
        methods=["GET"],
        auth="user",
        type="http",
        readonly=True,
        save_session=False,
    )
    def doc_index(self):
        endpoints = self._get_accessible_endpoints()
        result = {}
        for ep in endpoints:
            result.setdefault(ep.route_group, []).append(self._endpoint_to_doc(ep))
        return request.make_json_response(result)

    @http.route(
        "/json2/doc/<string:route_group>",
        methods=["GET"],
        auth="user",
        type="http",
        readonly=True,
        save_session=False,
    )
    def doc_domain(self, route_group):
        endpoints = self._get_accessible_endpoints([("route_group", "=", route_group)])
        if not endpoints:
            raise NotFound(f"No endpoints found for domain {route_group!r}")
        return request.make_json_response(
            [self._endpoint_to_doc(ep) for ep in endpoints]
        )
