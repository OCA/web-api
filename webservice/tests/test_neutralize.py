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
                "oauth2_clientid": "secret-client-id",
                "oauth2_client_secret": "secret-client-secret",
                "oauth2_client_auth_value": "secret-header-value",
                "oauth2_token": '{"access_token": "secret-token"}',
            }
        )
        return res

    def test_neutralize_removes_webservice_credentials(self):
        """Test database neutralization clears stored webservice backend credentials."""
        installed_modules = neutralize.get_installed_modules(self.cr)
        queries = neutralize.get_neutralization_queries(installed_modules)
        for query in queries:
            self.cr.execute(query)
        self.backend.invalidate_recordset()
        self.assertFalse(self.backend.username)
        self.assertFalse(self.backend.password)
        self.assertFalse(self.backend.api_key)
        self.assertFalse(self.backend.oauth2_clientid)
        self.assertFalse(self.backend.oauth2_client_secret)
        self.assertFalse(self.backend.oauth2_client_auth_value)
        self.assertFalse(self.backend.oauth2_token)
