# Copyright 2026 Camptocamp SA
# @author Simone Orsi <simahawk@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import responses
from psycopg2 import errors as pg_errors

from odoo import exceptions
from odoo.tests.common import tagged
from odoo.tools import mute_logger

from .common import CommonWebService


@tagged("-at_install", "post_install")
class TestWebserviceEndpoint(CommonWebService):
    @classmethod
    def _setup_records(cls):
        res = super()._setup_records()
        cls.url = "https://localhost.demo.odoo/"
        cls.backend = cls.env["webservice.backend"].create(
            {
                "name": "WebService",
                "protocol": "http",
                "url": cls.url,
                "content_type": "application/xml",
                "tech_name": "demo_ws",
                "auth_type": "api_key",
                "api_key": "backend-key",
                "api_key_header": "Api-Key",
            }
        )
        cls.endpoint = cls.env["webservice.endpoint"].create(
            {
                "name": "Get Order Status",
                "tech_name": "get_order_status",
                "description": "Retrieve the status of an order",
                "backend_id": cls.backend.id,
                "http_method": "get",
                "path": "orders/{order_id}/status",
            }
        )
        return res

    def test_tech_name_unique_per_backend(self):
        with (
            mute_logger("odoo.sql_db"),
            self.assertRaises(pg_errors.UniqueViolation),
            self.cr.savepoint(),
        ):
            self.env["webservice.endpoint"].create(
                {
                    "name": "Duplicate",
                    "tech_name": "get_order_status",
                    "description": "Duplicate tech_name on the same backend",
                    "backend_id": self.backend.id,
                    "http_method": "post",
                }
            )

    def test_tech_name_unique_across_backends_ok(self):
        other_backend = self.backend.copy({"tech_name": "demo_ws_2"})
        # Same ``tech_name`` on a different backend is allowed.
        endpoint = self.env["webservice.endpoint"].create(
            {
                "name": "Get Order Status",
                "tech_name": "get_order_status",
                "description": "Same tech_name, different backend",
                "backend_id": other_backend.id,
                "http_method": "get",
            }
        )
        self.assertTrue(endpoint)

    def test_override_auth_requires_auth_type(self):
        with self.assertRaises(exceptions.UserError):
            self.endpoint.write({"override_auth": True})

    @responses.activate
    def test_call_delegates_to_backend_auth(self):
        url = f"{self.url}orders/42/status"
        responses.add(responses.GET, url, body="{}")
        result = self.endpoint.call(url_params={"order_id": 42})
        self.assertEqual(result.content, b"{}")
        self.assertEqual(len(responses.calls), 1)
        # No override: the backend's own API key is used.
        self.assertEqual(responses.calls[0].request.headers["Api-Key"], "backend-key")
        self.assertEqual(
            responses.calls[0].request.headers["Content-Type"], "application/xml"
        )

    @responses.activate
    def test_call_with_override_auth_uses_own_credentials(self):
        self.endpoint.write(
            {
                "override_auth": True,
                "auth_type": "api_key",
                "api_key": "endpoint-key",
                "api_key_header": "Api-Key",
                "content_type": "application/json",
            }
        )
        url = f"{self.url}orders/42/status"
        responses.add(responses.GET, url, body="{}")
        result = self.endpoint.call(url_params={"order_id": 42})
        self.assertEqual(result.content, b"{}")
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.headers["Api-Key"], "endpoint-key")
        self.assertEqual(
            responses.calls[0].request.headers["Content-Type"], "application/json"
        )

    @responses.activate
    def test_call_merges_static_headers(self):
        self.endpoint.write(
            {"header_ids": [(0, 0, {"name": "X-Demo", "value": "demo-value"})]}
        )
        url = f"{self.url}orders/42/status"
        responses.add(responses.GET, url, body="{}")
        self.endpoint.call(url_params={"order_id": 42})
        self.assertEqual(responses.calls[0].request.headers["X-Demo"], "demo-value")

    @responses.activate
    def test_call_headers_override_static_headers(self):
        self.endpoint.write(
            {"header_ids": [(0, 0, {"name": "X-Demo", "value": "demo-value"})]}
        )
        url = f"{self.url}orders/42/status"
        responses.add(responses.GET, url, body="{}")
        self.endpoint.call(
            url_params={"order_id": 42}, headers={"X-Demo": "call-time-value"}
        )
        self.assertEqual(
            responses.calls[0].request.headers["X-Demo"], "call-time-value"
        )

    @responses.activate
    def test_call_sends_default_querystring_params(self):
        self.endpoint.write(
            {"querystring_param_ids": [(0, 0, {"name": "verbose", "value": "1"})]}
        )
        url = f"{self.url}orders/42/status"
        responses.add(responses.GET, url, body="{}")
        self.endpoint.call(url_params={"order_id": 42})
        self.assertIn("verbose=1", responses.calls[0].request.url)

    @responses.activate
    def test_call_params_kwarg_overrides_default(self):
        self.endpoint.write(
            {"querystring_param_ids": [(0, 0, {"name": "verbose", "value": "1"})]}
        )
        url = f"{self.url}orders/42/status"
        responses.add(responses.GET, url, body="{}")
        self.endpoint.call(url_params={"order_id": 42}, params={"verbose": "0"})
        self.assertIn("verbose=0", responses.calls[0].request.url)

    @responses.activate
    def test_call_querystring_param_value_placeholder_resolved(self):
        # A configured querystring param value may itself contain a
        # `{placeholder}`, resolved against the same `url_params` used for
        # the URL path.
        self.endpoint.write(
            {
                "querystring_param_ids": [
                    (0, 0, {"name": "ref", "value": "order-{order_id}"})
                ]
            }
        )
        url = f"{self.url}orders/42/status"
        responses.add(responses.GET, url, body="{}")
        self.endpoint.call(url_params={"order_id": 42})
        self.assertIn("ref=order-42", responses.calls[0].request.url)

    @responses.activate
    def test_call_merges_backend_and_endpoint_headers_endpoint_wins(self):
        self.backend.write(
            {"header_ids": [(0, 0, {"name": "X-Demo", "value": "backend-value"})]}
        )
        self.endpoint.write(
            {"header_ids": [(0, 0, {"name": "X-Demo", "value": "endpoint-value"})]}
        )
        url = f"{self.url}orders/42/status"
        responses.add(responses.GET, url, body="{}")
        self.endpoint.call(url_params={"order_id": 42})
        self.assertEqual(responses.calls[0].request.headers["X-Demo"], "endpoint-value")

    @responses.activate
    def test_call_inherits_backend_headers_when_endpoint_has_none(self):
        self.backend.write(
            {"header_ids": [(0, 0, {"name": "X-Backend", "value": "backend-value"})]}
        )
        url = f"{self.url}orders/42/status"
        responses.add(responses.GET, url, body="{}")
        self.endpoint.call(url_params={"order_id": 42})
        self.assertEqual(
            responses.calls[0].request.headers["X-Backend"], "backend-value"
        )

    @responses.activate
    def test_backend_call_uses_own_header_and_querystring_param_defaults(self):
        self.backend.write(
            {
                "header_ids": [(0, 0, {"name": "X-Backend", "value": "1"})],
                "querystring_param_ids": [(0, 0, {"name": "verbose", "value": "1"})],
            }
        )
        responses.add(responses.GET, self.url, body="{}")
        self.backend.call("get")
        self.assertEqual(responses.calls[0].request.headers["X-Backend"], "1")
        self.assertIn("verbose=1", responses.calls[0].request.url)

    def test_header_line_gets_res_model_and_res_id_set(self):
        self.backend.write({"header_ids": [(0, 0, {"name": "X", "value": "1"})]})
        line = self.backend.header_ids
        self.assertEqual(line.res_model, "webservice.backend")
        self.assertEqual(line.res_id, self.backend.id)

    def test_display_name_default(self):
        self.assertEqual(self.endpoint.display_name, "Get Order Status")

    def test_display_name_with_path_via_context(self):
        endpoint = self.endpoint.with_context(webservice_endpoint_display_path=1)
        self.assertEqual(
            endpoint.display_name, "Get Order Status (orders/{order_id}/status)"
        )

    def test_display_name_with_path_via_context_no_path(self):
        endpoint = self.endpoint.copy({"tech_name": "no_path", "path": False})
        endpoint = endpoint.with_context(webservice_endpoint_display_path=1)
        self.assertEqual(endpoint.display_name, "Get Order Status")
