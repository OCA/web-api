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

    def _request(self, method, url=None, url_params=None, **kwargs):
        if self.auth_type == "client_certificate":
            # ``requests`` ``cert`` parameter accepts:
            # * A string: path to a file containing both certificate and private key
            # * A tuple: ('/path/client.cert', '/path/client.key')
            cert_path = self._get_cert_path()
            key_path = self._get_key_path()

            if "cert" not in kwargs and cert_path:
                if key_path:
                    kwargs["cert"] = (cert_path, key_path)
                else:
                    kwargs["cert"] = cert_path

        return super()._request(method, url=url, url_params=url_params, **kwargs)

    def _get_cert_path(self):
        return self.client_certificate_path

    def _get_key_path(self):
        return self.client_private_key_path
