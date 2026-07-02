# Copyright 2020 Creu Blanca
# Copyright 2022 Camptocamp SA
# @author Simone Orsi <simahawk@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class WebserviceBackend(models.Model):
    _name = "webservice.backend"
    _inherit = ["webservice.backend", "server.env.techname.mixin", "server.env.mixin"]

    @property
    def _server_env_fields(self):
        base_fields = super()._server_env_fields
        webservice_fields = {
            "protocol": {},
            "url": {},
            "auth_type": {},
            "username": {},
            "password": {},
            "api_key": {},
            "api_key_header": {},
            "content_type": {},
            "oauth2_flow": {},
            "oauth2_scope": {},
            "oauth2_clientid": {},
            "oauth2_client_secret": {},
            "oauth2_authorization_url": {},
            "oauth2_token_url": {},
            "oauth2_audience": {},
            "oauth2_token_method": {},
            "oauth2_client_auth_method": {},
            "oauth2_client_auth_header": {},
            "oauth2_client_auth_value": {},
        }
        webservice_fields.update(base_fields)
        return webservice_fields

    def _compute_server_env(self):
        # OVERRIDE: reset ``oauth2_flow`` when ``auth_type`` is not "oauth2", even if
        # defined otherwise in server env vars
        res = super()._compute_server_env()
        self.filtered(lambda r: r.auth_type != "oauth2").oauth2_flow = None
        return res
