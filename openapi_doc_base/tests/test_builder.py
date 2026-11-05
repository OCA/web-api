# Copyright 2026 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import functools
from types import SimpleNamespace

from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger

from ..builder import SpecBuilder, openapi_path

ITEM = {
    "type": "object",
    "required": ["name"],
    "properties": {"name": {"type": "string"}, "qty": {"type": "integer"}},
}


class SchemaParam:
    """Any object w/ `to_json_schema` can describe params."""

    def __init__(self, schema):
        self.schema = schema

    def to_json_schema(self, ctx, direction):
        if self.schema == "boom":
            raise ValueError("No request")
        return self.schema


def handler(**kw):
    """Do something.

    Long description.
    """


def _endpoint(**routing):
    endpoint = functools.partial(handler)
    functools.update_wrapper(endpoint, handler)
    endpoint.routing = dict({"type": "http", "auth": "user"}, **routing)
    return endpoint


class TestBuilder(TransactionCase):
    def _build(self, rules, **kw):
        return SpecBuilder(self.env, rules, title="Test", **kw).build()

    def test_openapi_path(self):
        """Path converters become `{name}` path params w/ their types."""
        path, params = openapi_path('/a/<int:id>/<model("res.partner"):p>/<name>')
        self.assertEqual(path, "/a/{id}/{p}/{name}")
        self.assertEqual(
            [(p["name"], p["schema"]["type"]) for p in params],
            [("id", "integer"), ("p", "integer"), ("name", "string")],
        )

    def test_operations(self):
        """Operations follow the rule; excluded rules are hidden."""
        rules = [
            (
                "/items/<int:id>",
                _endpoint(
                    methods=["GET", "POST", "OPTIONS"],
                    input=SchemaParam(ITEM),
                    output=SchemaParam(ITEM),
                    api_doc={"tags": ["items"], "deprecated": True},
                ),
            ),
            ("/hidden", _endpoint(api_doc={"exclude": True})),
        ]
        spec = self._build(rules, parameters=[{"name": "X", "in": "header"}])
        self.assertEqual(spec["openapi"], "3.0.3")
        self.assertEqual(list(spec["paths"]), ["/items/{id}"])
        path = spec["paths"]["/items/{id}"]
        self.assertEqual(sorted(path), ["get", "post"])
        get, post = path["get"], path["post"]
        self.assertEqual(get["summary"], "Do something.")
        self.assertEqual(get["description"], "Long description.")
        self.assertEqual(get["tags"], ["items"])
        self.assertTrue(get["deprecated"])
        self.assertEqual(get["operationId"], "get_items_id")
        self.assertEqual(get["security"], [{"odooSession": []}])
        self.assertIn("odooSession", spec["components"]["securitySchemes"])
        self.assertEqual(
            [(p["name"], p["in"], p.get("required")) for p in get["parameters"]],
            [
                ("id", "path", True),
                ("X", "header", None),
                ("name", "query", True),
                ("qty", "query", False),
            ],
        )
        self.assertNotIn("requestBody", get)
        self.assertEqual(
            post["requestBody"]["content"]["application/json"]["schema"], ITEM
        )
        self.assertEqual(
            post["responses"]["200"]["content"]["application/json"]["schema"], ITEM
        )
        self.assertIn("404", post["responses"])

    def test_api_doc_texts_and_no_security(self):
        """`api_doc` sets summary and operation id; public routes have no security."""
        rules = [
            (
                "/public",
                _endpoint(
                    auth="public",
                    methods=["GET"],
                    api_doc={"summary": "Sum", "operation_id": "my_op"},
                ),
            )
        ]
        spec = self._build(rules)
        op = spec["paths"]["/public"]["get"]
        self.assertEqual(op["summary"], "Sum")
        self.assertNotIn("description", op)
        self.assertEqual(op["operationId"], "my_op")
        self.assertNotIn("security", op)
        self.assertNotIn("components", spec)

    @mute_logger("odoo.addons.openapi_doc_base.builder")
    def test_broken_schema(self):
        """A schema that cannot be built is skipped, the operation stays."""
        rules = [("/broken", _endpoint(methods=["POST"], input=SchemaParam("boom")))]
        op = self._build(rules)["paths"]["/broken"]["post"]
        self.assertNotIn("requestBody", op)

    def test_api_doc_schemas(self):
        """Input and output schemas and content type come from `api_doc`."""
        # Plain objects w/ routing are enough (eg: built from records)
        endpoint = SimpleNamespace(
            routing={
                "auth": "api_key",
                "methods": ["POST"],
                "api_doc": {
                    "summary": "Import",
                    "input_schema": ITEM,
                    "output_schema": ITEM,
                    "content_type": "application/xml",
                },
            }
        )
        spec = self._build([("/import", endpoint)])
        op = spec["paths"]["/import"]["post"]
        self.assertEqual(
            op["requestBody"]["content"]["application/xml"]["schema"], ITEM
        )
        self.assertEqual(
            op["responses"]["200"]["content"]["application/json"]["schema"], ITEM
        )
        self.assertEqual(op["security"], [{"apiKey": []}])
