# Copyright 2020 Creu Blanca
# Copyright 2022 Camptocamp SA
# @author Simone Orsi <simahawk@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class WebserviceBackend(models.Model):

    _name = "webservice.backend"
    _inherit = ["server.env.techname.mixin", "server.env.mixin"]

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
        }
        webservice_fields.update(base_fields)
        return webservice_fields
