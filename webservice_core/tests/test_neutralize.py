# Copyright 2026 Camptocamp SA
# @author Simone Orsi <simone.orsi@camptocamp.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.modules import neutralize
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestNeutralize(TransactionCase):
    """Check the neutralization script on the raw database columns.

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
                "name": "Neutralize me",
                "tech_name": "neutralize_me",
                "protocol": "http",
                "url": "https://production.example.com/api",
            }
        )
        cls.env.flush_all()
        cls.env.cr.execute(
            """
            UPDATE webservice_backend
               SET url = %s, username = %s, password = %s, api_key = %s
             WHERE id = %s
            """,
            (
                "https://production.example.com/api",
                "prod_user",
                "prod_password",
                "prod_api_key",
                cls.backend.id,
            ),
        )
        cls.public_param, cls.secret_param = cls.env[
            "webservice.querystring.param"
        ].create(
            [
                {
                    "res_model": cls.backend._name,
                    "res_id": cls.backend.id,
                    "name": "lang",
                    "value": "en",
                },
                {
                    "res_model": cls.backend._name,
                    "res_id": cls.backend.id,
                    "name": "token",
                    "value": "prod_token",
                    "secret": True,
                },
            ]
        )
        cls.public_header, cls.secret_header = cls.env["webservice.header"].create(
            [
                {
                    "res_model": cls.backend._name,
                    "res_id": cls.backend.id,
                    "name": "Accept-Language",
                    "value": "en",
                },
                {
                    "res_model": cls.backend._name,
                    "res_id": cls.backend.id,
                    "name": "X-Token",
                    "value": "prod_token",
                    "secret": True,
                },
            ]
        )
        cls.env.flush_all()

    def _run_neutralize(self):
        """Run the neutralization queries of the webservice_core module."""
        for query in neutralize.get_neutralization_queries(["webservice_core"]):
            self.env.cr.execute(query)

    def _read_backend_row(self):
        """Return the raw database values of the test backend."""
        self.env.cr.execute(
            """
            SELECT name, url, username, password, api_key
              FROM webservice_backend
             WHERE id = %s
            """,
            (self.backend.id,),
        )
        return self.env.cr.dictfetchone()

    def _read_param_value(self, param):
        """Return the raw database value of a querystring param."""
        self.env.cr.execute(
            "SELECT value FROM webservice_querystring_param WHERE id = %s",
            (param.id,),
        )
        return self.env.cr.fetchone()[0]

    def _read_header_value(self, header):
        """Return the raw database value of a header."""
        self.env.cr.execute(
            "SELECT value FROM webservice_header WHERE id = %s", (header.id,)
        )
        return self.env.cr.fetchone()[0]

    def test_neutralize_replaces_url(self):
        """The production URL is replaced by a placeholder."""
        self._run_neutralize()
        self.assertEqual(self._read_backend_row()["url"], "https://neutralized.invalid")

    def test_neutralize_clears_credentials(self):
        """Username, password and API key of the backend are cleared."""
        self._run_neutralize()
        row = self._read_backend_row()
        self.assertIsNone(row["username"])
        self.assertIsNone(row["password"])
        self.assertIsNone(row["api_key"])

    def test_neutralize_keeps_other_fields(self):
        """Fields that are not endpoints or credentials are left untouched."""
        self._run_neutralize()
        self.assertEqual(self._read_backend_row()["name"], "Neutralize me")

    def test_neutralize_replaces_secret_param_value(self):
        """The value of a secret querystring param is replaced."""
        self._run_neutralize()
        self.assertEqual(self._read_param_value(self.secret_param), "neutralized")

    def test_neutralize_keeps_public_param_value(self):
        """The value of a non secret querystring param is left untouched."""
        self._run_neutralize()
        self.assertEqual(self._read_param_value(self.public_param), "en")

    def test_neutralize_replaces_secret_header_value(self):
        """The value of a secret header is replaced."""
        self._run_neutralize()
        self.assertEqual(self._read_header_value(self.secret_header), "neutralized")

    def test_neutralize_keeps_public_header_value(self):
        """The value of a non secret header is left untouched."""
        self._run_neutralize()
        self.assertEqual(self._read_header_value(self.public_header), "en")
