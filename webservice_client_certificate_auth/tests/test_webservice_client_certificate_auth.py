# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import os
from unittest import mock

from odoo import exceptions

from odoo.addons.webservice.tests.common import CommonWebService


class TestClientCertAuth(CommonWebService):
    @classmethod
    def _setup_records(cls):
        res = super()._setup_records()
        cls.url = "https://localhost.demo.odoo/"
        # Certificate and private key configuration
        os.environ["SERVER_ENV_CONFIG"] = "\n".join(
            [
                "[webservice_backend.test_client_certificate_and_key]",
                "auth_type = client_certificate",
                "client_certificate_path = /path/client.cert",
                "client_private_key_path = /path/client.key",
            ]
        )
        cls.backend_certificate_and_key = cls.env["webservice.backend"].create(
            {
                "name": "Webservice Client Certificate & Key",
                "tech_name": "test_client_certificate_and_key",
                "protocol": "http",
                "url": cls.url,
                "auth_type": "client_certificate",
                "client_certificate_path": "/path/client.cert",
                "client_private_key_path": "/path/client.key",
            }
        )
        # Certificate only configuration (no private key)
        os.environ["SERVER_ENV_CONFIG"] = "\n".join(
            [
                "[webservice_backend.test_client_certificate_only]",
                "auth_type = client_certificate",
                "client_certificate_path = /path/client.pem",
            ]
        )
        cls.backend_certificate_only = cls.env["webservice.backend"].create(
            {
                "name": "Webservice Client Certificate Only",
                "tech_name": "test_client_certificate_only",
                "protocol": "http",
                "url": cls.url,
                "auth_type": "client_certificate",
                "client_certificate_path": "/path/client.pem",
            }
        )
        return res

    def test_request_adapter_certificate_and_key(self):
        with mock.patch("requests.request") as mock_request:
            mock_request.return_value.content = b"{}"
            mock_request.return_value.status_code = 200

            self.backend_certificate_and_key.call("get", url=f"{self.url}endpoint")

            self.assertTrue(mock_request.called)
            _args, kwargs = mock_request.call_args

            # Verify 'cert' is passed as a tuple (cert, key)
            self.assertIn("cert", kwargs)
            self.assertEqual(kwargs["cert"], ("/path/client.cert", "/path/client.key"))

    def test_request_adapter_certificate_only(self):
        with mock.patch("requests.request") as mock_request:
            mock_request.return_value.content = b"{}"
            mock_request.return_value.status_code = 200

            self.backend_certificate_only.call("get", url=f"{self.url}endpoint")

            self.assertTrue(mock_request.called)
            _args, kwargs = mock_request.call_args

            # Verify 'cert' is a simple string
            self.assertEqual(kwargs["cert"], "/path/client.pem")

    def test_auth_type_validation(self):
        with self.assertRaisesRegex(
            exceptions.UserError, "requires 'Client Certificate'"
        ):
            self.env["webservice.backend"].create(
                {
                    "name": "Broken Service",
                    "tech_name": "broken_config",
                    "protocol": "http",
                    "url": "http://localhost",
                    "auth_type": "client_certificate",
                }
            )
