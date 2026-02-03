# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class WebserviceBackend(models.Model):
    _inherit = "webservice.backend"

    auth_type = fields.Selection(
        selection_add=[("client_certificate", "Client Certificate")],
        ondelete={"client_certificate": lambda recs: recs.write({"auth_type": "none"})},
    )
    client_certificate_path = fields.Char(
        auth_type="client_certificate",
    )
    client_private_key_path = fields.Char()

    @property
    def _server_env_fields(self):
        env_fields = super()._server_env_fields
        env_fields.update(
            {
                "client_certificate_path": {},
                "client_private_key_path": {},
            }
        )
        return env_fields
