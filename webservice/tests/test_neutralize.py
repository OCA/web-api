# Copyright 2026 Camptocamp SA
# @author Simone Orsi <simone.orsi@camptocamp.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.modules import neutralize
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestNeutralize(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.backend = cls.env["webservice.backend"].create(
            {
                "name": "Neutralize OAuth2",
                "tech_name": "neutralize_oauth2",
                "protocol": "http",
                "url": "https://production.example.com/api",
                "oauth2_clientid": "prod_client_id",
                "oauth2_client_secret": "prod_client_secret",
                "oauth2_token": "prod_token",
            }
        )

    def _run_neutralize(self):
        """Run the neutralization queries of the webservice module."""
        for query in neutralize.get_neutralization_queries(["webservice"]):
            self.env.cr.execute(query)
        self.backend.invalidate_recordset()

    def test_neutralize_clears_oauth2_secrets(self):
        """OAuth2 client ID, client secret and token are cleared."""
        self._run_neutralize()
        self.assertFalse(self.backend.oauth2_clientid)
        self.assertFalse(self.backend.oauth2_client_secret)
        self.assertFalse(self.backend.oauth2_token)

    def test_neutralize_keeps_endpoint(self):
        """The endpoint is not touched by the OAuth2 neutralization."""
        self._run_neutralize()
        self.assertEqual(self.backend.url, "https://production.example.com/api")
