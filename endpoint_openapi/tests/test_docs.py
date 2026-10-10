# Copyright 2026 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import json

from odoo import exceptions
from odoo.tests.common import HttpCase, new_test_user, tagged

SCHEMA = {
    "type": "object",
    "required": ["ref"],
    "properties": {"ref": {"type": "string"}},
}


class CommonDocs:
    @classmethod
    def _create_endpoints(cls):
        model = cls.env["endpoint.endpoint"]
        common = {"exec_mode": "code", "code_snippet": "result = {}"}
        cls.ep_import = model.create(
            dict(
                common,
                name="Import orders",
                route="/test_doc/orders",
                request_method="POST",
                request_content_type="application/xml",
                route_group="orders",
                api_doc_enabled=True,
                api_doc_description="Import orders from XML.",
                api_doc_tags="orders, import",
                api_doc_input_schema=json.dumps(SCHEMA),
            )
        )
        cls.ep_status = model.create(
            dict(
                common,
                name="Order status",
                route="/test_doc/status",
                request_method="GET",
                route_group="orders",
                api_doc_enabled=True,
                api_doc_output_schema=json.dumps(SCHEMA),
            )
        )
        cls.ep_hidden = model.create(
            dict(
                common,
                name="Internal",
                route="/test_doc/internal",
                request_method="GET",
                route_group="orders",
            )
        )
        cls.ep_other = model.create(
            dict(
                common,
                name="Ping",
                route="/test_doc/ping",
                request_method="GET",
                auth_type="public",
                exec_as_user_id=cls.env.ref("base.user_admin").id,
                api_doc_enabled=True,
            )
        )


@tagged("-at_install", "post_install")
class TestDocs(HttpCase, CommonDocs):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._create_endpoints()
        cls.ir_http = cls.env["ir.http"]
        new_test_user(
            cls.env,
            login="doc_user",
            password="doc_user",
            groups="base.group_user,openapi_doc_base.group_openapi_doc_viewer",
        )

    def test_sources(self):
        """There is one source per model and route group (`default` if none)."""
        sources = self.ir_http._openapi_doc_sources_for(category="endpoint.endpoint")
        self.assertEqual(
            [(s.key, s.app) for s in sources],
            [
                ("endpoint.endpoint.default", "default"),
                ("endpoint.endpoint.orders", "orders"),
            ],
        )

    def test_document(self):
        """A group's document lists the enabled endpoints w/ schemas, auth and tags."""
        doc = self.ir_http._openapi_doc("endpoint.endpoint.orders")
        self.assertEqual(sorted(doc["paths"]), ["/test_doc/orders", "/test_doc/status"])
        post = doc["paths"]["/test_doc/orders"]["post"]
        self.assertEqual(post["summary"], "Import orders")
        self.assertEqual(post["description"], "Import orders from XML.")
        self.assertEqual(post["tags"], ["orders", "import"])
        self.assertEqual(
            post["requestBody"]["content"]["application/xml"]["schema"], SCHEMA
        )
        self.assertEqual(post["security"], [{"odooSession": []}])
        get = doc["paths"]["/test_doc/status"]["get"]
        self.assertEqual(
            get["responses"]["200"]["content"]["application/json"]["schema"], SCHEMA
        )
        doc = self.ir_http._openapi_doc("endpoint.endpoint.default")
        op = doc["paths"]["/test_doc/ping"]["get"]
        self.assertNotIn("security", op)

    def test_doc_refreshed(self):
        """Disabling the docs of an endpoint removes it from its document."""
        self.assertIn(
            "/test_doc/status",
            self.ir_http._openapi_doc("endpoint.endpoint.orders")["paths"],
        )
        self.ep_status.api_doc_enabled = False
        self.assertNotIn(
            "/test_doc/status",
            self.ir_http._openapi_doc("endpoint.endpoint.orders")["paths"],
        )

    def test_schema_validation(self):
        """Invalid schemas (not JSON objects) are refused."""
        with self.assertRaises(exceptions.ValidationError):
            self.ep_status.api_doc_output_schema = "[1, 2]"
        with self.assertRaises(exceptions.ValidationError):
            self.ep_status.api_doc_output_schema = "{nope"

    def test_http(self):
        """Viewers get the endpoint docs; internal users w/o the group get a 404."""
        self.authenticate("doc_user", "doc_user")
        response = self.url_open("/openapi/docs?category=endpoint.endpoint")
        self.assertEqual(response.status_code, 200)
        self.assertIn("/openapi/docs/endpoint.endpoint.orders.json", response.text)
        self.assertIn("app=orders", response.text)
        response = self.url_open("/openapi/docs/endpoint.endpoint.orders.json")
        self.assertIn("/test_doc/orders", response.json()["paths"])
        # Internal users w/o the viewer group can't see the docs
        new_test_user(self.env, login="internal", password="internal")
        self.authenticate("internal", "internal")
        response = self.url_open("/openapi/docs/endpoint.endpoint.orders.json")
        self.assertEqual(response.status_code, 404)
