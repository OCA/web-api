# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.modules import neutralize
from odoo.tests import tagged

from odoo.addons.webservice.tests.common import CommonWebService


@tagged("neutralize")
class TestWebserviceServerEnvNeutralize(CommonWebService):
    @classmethod
    def _setup_records(cls):
        res = super()._setup_records()
        # No `SERVER_ENV_CONFIG` section is defined for this tech_name, so
        # these credentials are stored as env-default values inside
        # `server_env_defaults` instead of the (now unused) plain columns.
        cls.backend = cls.env["webservice.backend"].create(
            {
                "name": "Neutralize WebService Server Env",
                "protocol": "http",
                "url": "https://localhost.demo.odoo/",
                "tech_name": "neutralize_server_env_ws",
                "auth_type": "none",
                "username": "secret-user",
                "password": "secret-password",
                "api_key": "secret-api-key",
                "oauth2_clientid": "secret-client-id",
                "oauth2_client_secret": "secret-client-secret",
                "oauth2_client_auth_value": "secret-header-value",
            }
        )
        return res

    def test_neutralize_removes_server_env_default_credentials(self):
        """Test neutralization clears credentials stored as server-env defaults."""
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
