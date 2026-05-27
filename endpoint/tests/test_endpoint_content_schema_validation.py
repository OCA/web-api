# Copyright 2026 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import json
import os
from unittest import mock, skipIf

from odoo import exceptions
from odoo.tests import Form, HttpCase
from odoo.tools.misc import mute_logger

from .common import CommonEndpoint, _setup_demo_records


class TestEndpointContentSchemaValidation(CommonEndpoint):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.endpoint_json = cls.env["endpoint.endpoint"].search(
            [("route", "=", "/demo/schema")]
        )
        cls.endpoint_xml = cls.env["endpoint.endpoint"].search(
            [("route", "=", "/demo/schema-xml")]
        )

    def test_request_content_schema_applicable_post_json(self):
        self.assertTrue(self.endpoint_json.request_content_schema_applicable)

    def test_request_content_schema_applicable_put_json(self):
        self.endpoint_json.request_method = "PUT"
        self.assertTrue(self.endpoint_json.request_content_schema_applicable)

    def test_request_content_schema_applicable_post_xml(self):
        self.assertTrue(self.endpoint_xml.request_content_schema_applicable)

    def test_request_content_schema_not_applicable_for_non_body_method(self):
        self.endpoint_json.write(
            {"request_method": "GET", "request_content_type": False}
        )
        self.assertFalse(self.endpoint_json.request_content_schema_applicable)

    def test_request_content_schema_not_applicable_for_unsupported_type(self):
        # Clear the schema first; otherwise the constraint would re-validate
        # the JSON Schema content as if it were the new (non-applicable) type.
        self.endpoint_json.request_content_schema = False
        self.endpoint_json.request_content_type = "text/plain"
        self.assertFalse(self.endpoint_json.request_content_schema_applicable)

    def test_request_content_schema_cleared_on_content_type_change(self):
        self.assertTrue(self.endpoint_json.request_content_schema)
        # Minimal view to bypass form inheritance from sibling modules that
        # may not be loaded when the endpoint module is tested in isolation.
        with Form(self.endpoint_json) as form:
            form.request_content_type = "application/xml"
            self.assertFalse(form.request_content_schema)

    def test_request_content_schema_invalid_yaml_raises(self):
        with self.assertRaisesRegex(
            exceptions.UserError, r"Invalid YAML/JSON in request content schema"
        ):
            self.endpoint_json.request_content_schema = "this: is: not: valid: yaml: ["

    def test_request_content_schema_invalid_jsonschema_raises(self):
        with self.assertRaisesRegex(
            exceptions.UserError, r"Invalid JSON Schema in request content schema"
        ):
            self.endpoint_json.request_content_schema = "type: not_a_real_type"

    def test_request_content_schema_valid_json_ok(self):
        self.endpoint_json.request_content_schema = json.dumps(
            {"type": "object", "required": ["data"]}
        )

    def test_request_content_schema_valid_xsd_ok(self):
        self.endpoint_xml.request_content_schema = (
            '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">'
            '<xs:element name="root" type="xs:string"/>'
            "</xs:schema>"
        )

    def test_request_content_schema_invalid_xml_raises(self):
        with self.assertRaisesRegex(
            exceptions.UserError, r"Invalid XML in request content schema"
        ):
            self.endpoint_xml.request_content_schema = "<not-valid-xml"

    def test_request_content_schema_invalid_xsd_raises(self):
        with self.assertRaisesRegex(
            exceptions.UserError, r"Invalid XML Schema \(XSD\)"
        ):
            self.endpoint_xml.request_content_schema = (
                '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">'
                '<xs:element name="root" type="xs:nonExistentType"/>'
                "</xs:schema>"
            )

    def test_request_content_schema_unknown_content_type_skipped(self):
        # text/plain is not in the applicable types; the constraint dispatch
        # is a no-op and any text passes.
        self.endpoint_json.request_content_type = "text/plain"
        self.endpoint_json.request_content_schema = "this is not JSON or XML"
        self.assertTrue(self.endpoint_json.request_content_schema)

    def test_validate_request_content_skipped_without_schema(self):
        self.endpoint_json.request_content_schema = False
        get_json_data = mock.Mock()
        with self._get_mocked_request(httprequest={"method": "POST"}) as req:
            req.get_json_data = get_json_data
            self.endpoint_json._validate_request_content(req)
        get_json_data.assert_not_called()

    def test_validate_request_content_skipped_for_non_applicable_type(self):
        self.endpoint_json.request_content_type = "text/plain"
        get_json_data = mock.Mock()
        with self._get_mocked_request(httprequest={"method": "POST"}) as req:
            req.get_json_data = get_json_data
            self.endpoint_json._validate_request_content(req)
        get_json_data.assert_not_called()


@skipIf(os.getenv("SKIP_HTTP_CASE"), "HttpCase skipped")
class TestEndpointContentSchemaValidationHttp(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _setup_demo_records(cls.env)
        cls.env["endpoint.endpoint"].search([])._handle_registry_sync()

    def tearDown(self):
        # Clear cache for method ``ir.http.routing_map()``
        self.env.registry.clear_cache("routing")
        super().tearDown()

    def test_json_valid_body(self):
        response = self.url_open(
            "/demo/schema",
            data=json.dumps({"data": [1, 2, 3]}),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content.decode()), {"ok": True})

    @mute_logger("endpoint.endpoint")
    def test_json_invalid_body(self):
        response = self.url_open(
            "/demo/schema",
            data=json.dumps({"data": "not-an-array"}),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 400)
        payload = json.loads(response.content.decode())
        self.assertEqual(payload["detail"][0]["loc"], ["body", "data"])
        self.assertEqual(payload["detail"][0]["type"], "type")

    @mute_logger("endpoint.endpoint")
    def test_validation_error_preserves_cors_headers(self):
        response = self.url_open(
            "/demo/schema",
            data=json.dumps({"data": "not-an-array"}),
            headers={
                "Content-Type": "application/json",
                "Origin": "https://editor.swagger.io",
            },
        )
        self.assertEqual(response.status_code, 400)
        # Route-managed CORS headers (default cors="*") must survive on the
        # validation-error response, not only on a successful one.
        self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), "*")

    @mute_logger("endpoint.endpoint")
    def test_json_malformed_body(self):
        response = self.url_open(
            "/demo/schema",
            data="not-json",
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 400)
        payload = json.loads(response.content.decode())
        self.assertEqual(payload["detail"][0]["type"], "json_invalid")

    def test_xml_valid_body(self):
        response = self.url_open(
            "/demo/schema-xml",
            data=b"<greeting>hello</greeting>",
            headers={"Content-Type": "application/xml"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content.decode()), {"ok": True})

    @mute_logger("endpoint.endpoint")
    def test_xml_invalid_body(self):
        response = self.url_open(
            "/demo/schema-xml",
            data=b"<unexpected>oops</unexpected>",
            headers={"Content-Type": "application/xml"},
        )
        self.assertEqual(response.status_code, 400)
        payload = json.loads(response.content.decode())
        self.assertEqual(payload["detail"][0]["type"], "xml_schema")

    @mute_logger("endpoint.endpoint")
    def test_xml_malformed_body(self):
        response = self.url_open(
            "/demo/schema-xml",
            data=b"not-xml",
            headers={"Content-Type": "application/xml"},
        )
        self.assertEqual(response.status_code, 400)
        payload = json.loads(response.content.decode())
        self.assertEqual(payload["detail"][0]["type"], "xml_invalid")
