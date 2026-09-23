# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.server_environment.tests.common import ServerEnvironmentCase


class TestClientCertAuthServerEnv(ServerEnvironmentCase):
    def test_client_certificate_server_env(self):
        client_certificate_config = """
            [webservice_backend.test_server_env]
            auth_type = client_certificate
            client_certificate_path = /path/client.cert
            client_private_key_path = /path/client.key
        """
        with self.load_config(public=client_certificate_config):
            backend = self.env["webservice.backend"].create(
                {
                    "name": "Test Server Env",
                    "tech_name": "test_server_env",
                    "protocol": "http",
                    "url": "https://localhost",
                    "auth_type": "none",
                }
            )
            backend.invalidate_recordset()
            self.assertEqual(backend.auth_type, "client_certificate")
            self.assertEqual(
                backend.client_certificate_path,
                "/path/client.cert",
            )
            self.assertEqual(
                backend.client_private_key_path,
                "/path/client.key",
            )
