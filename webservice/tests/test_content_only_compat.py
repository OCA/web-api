# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import responses

from .common import CommonWebService


class TestContentOnlyCompat(CommonWebService):
    """`content_only` removal, and its backward-compat system parameter.

    This lives in `webservice`, not `webservice_core`: the compat switch
    only matters for databases that already ran with the old
    `content_only=True` default, and that's `webservice`'s history, not
    `webservice_core`'s (a new, not-yet-released module nobody depends on
    with that old default).
    """

    @classmethod
    def _setup_records(cls):
        res = super()._setup_records()
        cls.url = "https://localhost.demo.odoo/"
        cls.webservice = cls.env["webservice.backend"].create(
            {
                "name": "WebService",
                "protocol": "http",
                "url": cls.url,
                "tech_name": "demo_ws_content_only",
                "auth_type": "none",
            }
        )
        return res

    @responses.activate
    def test_returns_full_response_by_default(self):
        responses.add(responses.GET, self.url, body="{}")
        result = self.webservice.call("get")
        self.assertEqual(result.content, b"{}")
        self.assertEqual(result.status_code, 200)

    @responses.activate
    def test_compat_param_restores_content_only(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "webservice.request_content_only", "1"
        )
        responses.add(responses.GET, self.url, body="{}")
        with self.assertLogs(
            "odoo.addons.webservice.models.webservice_backend", level="WARNING"
        ) as log_catcher:
            result = self.webservice.call("get")
        self.assertEqual(result, b"{}")
        self.assertTrue(
            any("webservice.request_content_only" in m for m in log_catcher.output)
        )

    @responses.activate
    def test_content_only_kwarg_is_ignored(self):
        """The removed `content_only` kwarg no longer has any effect."""
        responses.add(responses.GET, self.url, body="{}")
        with self.assertLogs(
            "odoo.addons.webservice.models.webservice_backend", level="WARNING"
        ) as log_catcher:
            result = self.webservice.call("get", content_only=True)
        self.assertEqual(result.content, b"{}")
        self.assertTrue(any("content_only" in m for m in log_catcher.output))
