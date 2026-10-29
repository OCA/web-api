# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.modules import neutralize
from odoo.tests import tagged

from .common import CommonWebService


@tagged("neutralize")
class TestWebserviceNeutralize(CommonWebService):
    @classmethod
    def _setup_records(cls):
        res = super()._setup_records()
        # `auth_type="none"` skips the `_check_auth_type` constraint so all
        # credential fields can be populated at once regardless of which
        # auth method would normally require them.
        cls.backend = cls.env["webservice.backend"].create(
            {
                "name": "Neutralize WebService",
                "protocol": "http",
                "url": "https://localhost.demo.odoo/",
                "tech_name": "neutralize_ws",
                "auth_type": "none",
                "username": "secret-user",
                "password": "secret-password",
                "api_key": "secret-api-key",
            }
        )
        cls.endpoint = cls.env["webservice.endpoint"].create(
            {
                "name": "Neutralize Endpoint",
                "tech_name": "neutralize_endpoint",
                "description": "Endpoint with its own credentials",
                "backend_id": cls.backend.id,
                "override_auth": True,
                "auth_type": "none",
                "username": "secret-endpoint-user",
                "password": "secret-endpoint-password",
                "api_key": "secret-endpoint-api-key",
            }
        )
        return res

    def test_neutralize_removes_webservice_credentials(self):
        """Test neutralization clears stored backend and endpoint credentials."""
        installed_modules = neutralize.get_installed_modules(self.cr)
        queries = neutralize.get_neutralization_queries(installed_modules)
        for query in queries:
            self.cr.execute(query)
        self.env.invalidate_all()
        for rec in (self.backend, self.endpoint):
            self.assertFalse(rec.username)
            self.assertFalse(rec.password)
            self.assertFalse(rec.api_key)
