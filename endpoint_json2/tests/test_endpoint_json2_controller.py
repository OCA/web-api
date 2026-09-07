# Copyright 2026 Quartile (https://www.quartile.co)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import json
import os
from datetime import datetime, timedelta
from unittest import skipIf

import pytz

from odoo import Command
from odoo.tests import new_test_user
from odoo.tests.common import HttpCase

CT_JSON = {"Content-Type": "application/json"}


@skipIf(os.getenv("SKIP_HTTP_CASE"), "HttpCase skipped")
class TestEndpointJson2Controller(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api_user = new_test_user(
            cls.env,
            "json2_api_user",
            groups="base.group_user",
        )
        key = (
            cls.api_user.with_user(cls.api_user)
            .env["res.users.apikeys"]
            ._generate(
                scope="rpc",
                name="test",
                expiration_date=datetime.now() + timedelta(days=1),
            )
        )
        cls.bearer = {"Authorization": f"Bearer {key}"}
        cls.model_partner = cls.env["ir.model"]._get("res.partner")
        cls.group_user = cls.env.ref("base.group_user")
        cls.endpoint = cls._create_endpoint(
            {
                "name": "get_partners",
                "route_group": "test_contacts",
                "json2_description": "Return partner records",
                "json2_method": "search_read",
                "json2_response_fields": "name\nemail",
                "json2_default_domain": '[["is_company", "=", true]]',
            }
        )
        cls.env["endpoint.json2.param"].create(
            [
                {
                    "endpoint_id": cls.endpoint.id,
                    "name": "domain",
                    "param_type": "list",
                    "required": False,
                    "default_value": "[]",
                    "sequence": 10,
                },
                {
                    "endpoint_id": cls.endpoint.id,
                    "name": "limit",
                    "param_type": "integer",
                    "required": False,
                    "default_value": "10",
                    "sequence": 20,
                },
                {
                    "endpoint_id": cls.endpoint.id,
                    "name": "fields",
                    "param_type": "list",
                    "required": False,
                    "sequence": 30,
                },
            ]
        )
        cls.env["endpoint.endpoint"].search([])._handle_registry_sync()

    @classmethod
    def _create_endpoint(cls, vals):
        # route is required but not precomputed in endpoint_route_handler;
        # auto-derive it until that is fixed upstream.
        defaults = {
            "route_group": "test",
            "exec_mode": "json2",
            "request_method": "POST",
            "request_content_type": "application/json",
            "auth_type": "bearer",
            "json2_model_id": cls.model_partner.id,
            "json2_group_ids": [Command.link(cls.group_user.id)],
        }
        defaults.update(vals)
        defaults.setdefault(
            "route", f"/json2/{defaults['route_group']}/{defaults['name']}"
        )
        return cls.env["endpoint.endpoint"].create(defaults)

    def tearDown(self):
        self.env.registry.clear_cache("routing")
        super().tearDown()

    def _call(self, route_group, endpoint_name, payload=None):
        url = f"/json2/{route_group}/{endpoint_name}"
        return self.url_open(
            url,
            data=json.dumps(payload or {}),
            headers=CT_JSON | self.bearer,
        )

    def _call_doc(self, path=""):
        url = f"/json2/doc{path}"
        self.authenticate("json2_api_user", "json2_api_user")
        return self.url_open(
            url,
            allow_redirects=False,
        )

    def test_dispatch_happy_path(self):
        res = self._call("test_contacts", "get_partners")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIsInstance(data, list)
        for row in data:
            self.assertIn("name", row)
            self.assertIn("email", row)
            self.assertNotIn("phone", row)

    def test_dispatch_with_limit(self):
        res = self._call("test_contacts", "get_partners", {"limit": 2})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertLessEqual(len(data), 2)

    def test_dispatch_not_found(self):
        res = self._call("test_contacts", "nonexistent")
        self.assertEqual(res.status_code, 404)

    def test_dispatch_inactive_endpoint(self):
        endpoint = self._create_endpoint(
            {"name": "inactive_test", "json2_method": "search_read", "active": False}
        )
        endpoint._handle_registry_sync()
        res = self._call("test", endpoint.name)
        self.assertEqual(res.status_code, 404)

    def test_dispatch_required_param_missing(self):
        endpoint = self._create_endpoint(
            {"name": "get_required", "json2_method": "search_read"}
        )
        self.env["endpoint.json2.param"].create(
            {
                "endpoint_id": endpoint.id,
                "name": "domain",
                "param_type": "list",
                "required": True,
            }
        )
        endpoint._handle_registry_sync()
        res = self._call("test", "get_required")
        self.assertEqual(res.status_code, 422)

    def test_dispatch_wrong_param_type(self):
        res = self._call("test_contacts", "get_partners", {"limit": "not_an_int"})
        self.assertEqual(res.status_code, 422)

    def test_dispatch_int_accepted_for_float(self):
        endpoint = self._create_endpoint(
            {
                "name": "float_test",
                "json2_method": "search_read",
                "json2_response_fields": "name",
            }
        )
        self.env["endpoint.json2.param"].create(
            {
                "endpoint_id": endpoint.id,
                "name": "limit",
                "param_type": "float",
            }
        )
        endpoint._handle_registry_sync()
        res = self._call("test", "float_test", {"limit": 5})
        self.assertEqual(res.status_code, 200)

    def test_dispatch_default_domain_applied(self):
        self.env["res.partner"].create({"name": "Test Individual", "is_company": False})
        res = self._call("test_contacts", "get_partners")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data)
        names = [row["name"] for row in data]
        self.assertNotIn("Test Individual", names)

    def test_dispatch_domain_merge(self):
        company = self.env["res.partner"].create(
            {"name": "MergeCo", "ref": "MERGE_TEST", "is_company": True}
        )
        res = self._call(
            "test_contacts",
            "get_partners",
            {"domain": [["ref", "=", "MERGE_TEST"]]},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], company.name)

    def test_dispatch_dotted_fields(self):
        country_jp = self.env["res.country"].search([("code", "=", "JP")], limit=1)
        self.assertTrue(country_jp)
        self.env["res.partner"].create(
            {
                "name": "DottedCo",
                "ref": "DOTTED_TEST",
                "is_company": True,
                "country_id": country_jp.id,
            }
        )
        endpoint = self._create_endpoint(
            {
                "name": "dotted_partners",
                "json2_method": "search_read",
                "json2_response_fields": "name\ncountry_id.name country",
            }
        )
        self.env["endpoint.json2.param"].create(
            {
                "endpoint_id": endpoint.id,
                "name": "domain",
                "param_type": "list",
            }
        )
        endpoint._handle_registry_sync()
        res = self._call(
            "test", "dotted_partners", {"domain": [["ref", "=", "DOTTED_TEST"]]}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "DottedCo")
        self.assertEqual(data[0]["country"], country_jp.name)
        self.assertNotIn("country_id", data[0])
        self.assertNotIn("country_id.name", data[0])

    def test_dispatch_group_access_denied(self):
        group = self.env["res.groups"].create({"name": "Secret API Group"})
        endpoint = self._create_endpoint(
            {
                "name": "restricted",
                "json2_method": "search_read",
                "json2_group_ids": [Command.link(group.id)],
            }
        )
        endpoint._handle_registry_sync()
        res = self._call("test", "restricted")
        self.assertEqual(res.status_code, 403)

    def test_dispatch_group_access_granted(self):
        group = self.env["res.groups"].create({"name": "Allowed API Group"})
        self.api_user.group_ids = [Command.link(group.id)]
        endpoint = self._create_endpoint(
            {
                "name": "allowed",
                "json2_method": "search_read",
                "json2_group_ids": [Command.link(group.id)],
            }
        )
        endpoint._handle_registry_sync()
        res = self._call("test", "allowed")
        self.assertEqual(res.status_code, 200)

    def test_doc(self):
        res = self._call_doc()
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("test_contacts", data)
        names = [ep["name"] for ep in data["test_contacts"]]
        self.assertIn("get_partners", names)

    def test_dispatch_code_snippet(self):
        partner = self.env["res.partner"].create(
            {"name": "Original Name", "ref": "SNIPPET_TEST"}
        )
        endpoint = self._create_endpoint(
            {
                "name": "update_name",
                "json2_code_snippet": (
                    'p = Model.search([("ref", "=", params["ref"])], limit=1)\n'
                    "if not p:\n"
                    '    raise exceptions.NotFound("Not found")\n'
                    'p.write({"name": params["new_name"]})\n'
                    'result = {"ref": p.ref, "name": p.name}\n'
                ),
            }
        )
        self.env["endpoint.json2.param"].create(
            [
                {
                    "endpoint_id": endpoint.id,
                    "name": "ref",
                    "param_type": "string",
                    "required": True,
                    "sequence": 10,
                },
                {
                    "endpoint_id": endpoint.id,
                    "name": "new_name",
                    "param_type": "string",
                    "required": True,
                    "sequence": 20,
                },
            ]
        )
        endpoint._handle_registry_sync()
        res = self._call(
            "test",
            "update_name",
            {"ref": "SNIPPET_TEST", "new_name": "Updated Name"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["name"], "Updated Name")
        partner.invalidate_recordset()
        self.assertEqual(partner.name, "Updated Name")

    def test_dispatch_code_snippet_missing_result(self):
        endpoint = self._create_endpoint(
            {"name": "bad_snippet", "json2_code_snippet": "x = 1"}
        )
        endpoint._handle_registry_sync()
        res = self._call("test", "bad_snippet")
        self.assertEqual(res.status_code, 500)

    def test_dispatch_with_alias(self):
        endpoint = self._create_endpoint(
            {
                "name": "aliased_partners",
                "json2_method": "search_read",
                "json2_response_fields": "name label\nemail",
            }
        )
        self.env["endpoint.json2.param"].create(
            {
                "endpoint_id": endpoint.id,
                "name": "limit",
                "param_type": "integer",
                "default_value": "5",
            }
        )
        endpoint._handle_registry_sync()
        res = self._call("test", "aliased_partners")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data)
        for row in data:
            self.assertIn("label", row)
            self.assertNotIn("name", row)
            self.assertIn("email", row)

    def test_response_language_forced(self):
        lang_ja = self.env["res.lang"]._activate_lang("ja_JP")
        self.api_user.lang = "en_US"
        category = self.env["res.partner.category"].create({"name": "Hospital"})
        category.update_field_translations("name", {"ja_JP": "病院"})
        self.assertEqual(category.with_context(lang="ja_JP").name, "病院")
        endpoint = self._create_endpoint(
            {
                "name": "get_categories",
                "json2_model_id": self.env["ir.model"]._get("res.partner.category").id,
                "json2_description": "Return partner categories",
                "json2_method": "search_read",
                "json2_response_fields": "name",
                "json2_default_domain": f'[["id", "=", {category.id}]]',
            }
        )
        endpoint._handle_registry_sync()
        # Without a forced language, the API user's language applies.
        res = self._call("test", "get_categories")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()[0]["name"], "Hospital")
        endpoint.json2_lang_id = lang_ja
        res = self._call("test", "get_categories")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()[0]["name"], "病院")

    def test_response_timezone_forced(self):
        category = self.env["res.partner.category"].create({"name": "TZ Test"})
        endpoint = self._create_endpoint(
            {
                "name": "get_tz_categories",
                "json2_model_id": self.env["ir.model"]._get("res.partner.category").id,
                "json2_description": "Return partner categories",
                "json2_method": "search_read",
                "json2_response_fields": "name\nwrite_date",
                "json2_default_domain": f'[["id", "=", {category.id}]]',
            }
        )
        endpoint._handle_registry_sync()
        utc_value = pytz.utc.localize(category.write_date)
        # Without a forced timezone, datetimes are rendered in UTC.
        res = self._call("test", "get_tz_categories")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()[0]["write_date"], utc_value.isoformat())
        endpoint.json2_tz = "Asia/Tokyo"
        res = self._call("test", "get_tz_categories")
        self.assertEqual(res.status_code, 200)
        tokyo_value = res.json()[0]["write_date"]
        self.assertEqual(
            tokyo_value, utc_value.astimezone(pytz.timezone("Asia/Tokyo")).isoformat()
        )
        # The offset is carried in the payload, so both renderings are the same
        # instant.
        self.assertEqual(datetime.fromisoformat(tokyo_value), utc_value)
