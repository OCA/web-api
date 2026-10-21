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
                "name": "Neutralize me",
                "tech_name": "neutralize_me",
                "protocol": "http",
                "url": "https://production.example.com/api",
                "username": "prod_user",
                "password": "prod_password",
                "api_key": "prod_api_key",
            }
        )

    def _run_neutralize(self):
        """Run the neutralization queries of the webservice_core module."""
        for query in neutralize.get_neutralization_queries(["webservice_core"]):
            self.env.cr.execute(query)
        self.backend.invalidate_recordset()

    def test_neutralize_replaces_url(self):
        """The production URL is replaced by a placeholder."""
        self._run_neutralize()
        self.assertEqual(self.backend.url, "https://neutralized.invalid")

    def test_neutralize_clears_credentials(self):
        """Username, password and API key of the backend are cleared."""
        self._run_neutralize()
        self.assertFalse(self.backend.username)
        self.assertFalse(self.backend.password)
        self.assertFalse(self.backend.api_key)

    def test_neutralize_keeps_other_fields(self):
        """Fields that are not endpoints or credentials are left untouched."""
        self._run_neutralize()
        self.assertEqual(self.backend.name, "Neutralize me")
        self.assertEqual(self.backend.protocol, "http")
