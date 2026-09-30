# Copyright 2020 Creu Blanca
# Copyright 2022 Camptocamp SA
# @author Simone Orsi <simahawk@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models
from odoo.tools import mute_logger

from odoo.addons.server_environment.models.server_env_mixin import _partialmethod


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

    def _server_env_transform_field_to_read_from_env(self, field):
        # OVERRIDE: give each env-managed field its own compute method. With the
        # shared ``_compute_server_env``, Odoo groups them all together: writing
        # one protects the others, and those not cached yet read as False
        # (e.g. ``auth_type`` in the OAuth2 constraints when writing
        # ``oauth2_client_auth_method``).
        res = super()._server_env_transform_field_to_read_from_env(field)
        compute_name = f"_compute_server_env_{field.name}"
        compute_method = _partialmethod(
            type(self)._compute_server_env_field, field.name, __name__=compute_name
        )
        # Mute message related to new safeguard (PR odoo/odoo#247151)
        with mute_logger("odoo.tests.common"):
            setattr(type(self), compute_name, compute_method)
        field.compute = compute_name
        return res

    def _compute_server_env_field(self, field_name):
        options = self._server_env_fields[field_name]
        for record in self:
            if record._server_env_has_key_defined(field_name):
                record._compute_server_env_from_config(field_name, options)
            else:
                record._compute_server_env_from_default(field_name, options)
        if field_name == "oauth2_flow":
            # reset ``oauth2_flow`` when ``auth_type`` is not "oauth2", even if
            # defined otherwise in server env vars
            self.filtered(lambda r: r.auth_type != "oauth2").oauth2_flow = None
