# Copyright 2026 Camptocamp SA
# @author Simone Orsi <simone.orsi@camptocamp.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.modules import neutralize
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestNeutralize(TransactionCase):
    """Check the OAuth2 neutralization script on the raw database columns.

    The script works at the SQL level, and modules like
    `webservice_server_env` make the ORM read these fields from the
    environment instead of the columns, so values are seeded and checked
    with plain SQL.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.backend = cls.env["webservice.backend"].create(
            {
                "name": "Neutralize OAuth2",
                "tech_name": "neutralize_oauth2",
                "protocol": "http",
                "url": "https://production.example.com/api",
            }
        )
        cls.env.flush_all()
        cls.env.cr.execute(
            """
            UPDATE webservice_backend
               SET url = %s,
                   oauth2_clientid = %s,
                   oauth2_client_secret = %s,
                   oauth2_client_auth_value = %s,
                   oauth2_token = %s
             WHERE id = %s
            """,
            (
                "https://production.example.com/api",
                "prod_client_id",
                "prod_client_secret",
                "prod_client_auth_value",
                "prod_token",
                cls.backend.id,
            ),
        )

    def _run_neutralize(self):
        """Run the neutralization queries of the webservice module."""
        for query in neutralize.get_neutralization_queries(["webservice"]):
            self.env.cr.execute(query)

    def _read_backend_row(self):
        """Return the raw database values of the test backend."""
        self.env.cr.execute(
            """
            SELECT url, oauth2_clientid, oauth2_client_secret,
                   oauth2_client_auth_value, oauth2_token
              FROM webservice_backend
             WHERE id = %s
            """,
            (self.backend.id,),
        )
        return self.env.cr.dictfetchone()

    def test_neutralize_clears_oauth2_secrets(self):
        """OAuth2 client ID, secrets and token are cleared."""
        self._run_neutralize()
        row = self._read_backend_row()
        self.assertIsNone(row["oauth2_clientid"])
        self.assertIsNone(row["oauth2_client_secret"])
        self.assertIsNone(row["oauth2_client_auth_value"])
        self.assertIsNone(row["oauth2_token"])

    def test_neutralize_keeps_endpoint(self):
        """The endpoint is not touched by the OAuth2 neutralization."""
        self._run_neutralize()
        self.assertEqual(
            self._read_backend_row()["url"], "https://production.example.com/api"
        )
