# Copyright 2023 Camptocamp SA
# @author Simone Orsi <simahawk@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo.tests.common import BaseCase

from odoo.addons.webservice_core.utils import (
    sanitize_url_for_log,
    sanitize_values_for_log,
)


class TestUtils(BaseCase):
    def test_url_cleanup(self):
        url = "https://custom.url/?a=1&apikey=secret&password=moresecret"
        self.assertEqual(sanitize_url_for_log(url), "https://custom.url/?a=1")

    def test_values_cleanup(self):
        """Secret and sensitive looking values are masked, the others kept."""
        values = {"X-Token": "secret", "Password": "moresecret", "lang": "en"}
        self.assertEqual(
            sanitize_values_for_log(values, secret_keys={"x-token"}),
            {"X-Token": "***", "Password": "***", "lang": "en"},
        )
        # the original values are left untouched
        self.assertEqual(values["X-Token"], "secret")
