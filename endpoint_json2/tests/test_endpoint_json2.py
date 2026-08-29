# Copyright 2026 Quartile (https://www.quartile.co)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import base64
import json
from datetime import date, datetime

from odoo import Command, fields
from odoo.exceptions import ValidationError

from odoo.addons.http_routing.tests.common import MockRequest

from .common import CommonEndpointJson2


class TestEndpointJson2(CommonEndpointJson2):
    def test_route_auto_computed(self):
        self.assertEqual(self.endpoint.route, "/json2/test_contacts/get_partners")

    def test_private_method_rejected(self):
        with self.assertRaises(ValidationError):
            self._create_endpoint(
                {"name": "bad", "json2_method": "_compute_display_name"}
            )

    def test_invalid_domain(self):
        with self.assertRaises(ValidationError):
            self.endpoint.json2_default_domain = "not valid json"
        with self.assertRaises(ValidationError):
            self.endpoint.json2_default_domain = '{"key": "value"}'

    def test_invalid_response_fields(self):
        with self.assertRaises(ValidationError):
            self.endpoint.json2_response_fields = "name\nnonexistent_field"
        with self.assertRaises(ValidationError):
            self.endpoint.json2_response_fields = "name\nnonexistent_id.name"
        with self.assertRaises(ValidationError):
            self.endpoint.json2_response_fields = "name\nemail.something"
        with self.assertRaises(ValidationError):
            self.endpoint.json2_response_fields = "name\ncountry_id.nonexistent"

    def test_plain_names_unvalidated_when_not_a_field_reader(self):
        """Neither is read/search_read, so their declared names go unchecked.

        The snippet body is never run by the constraint; it is only there
        because an endpoint needs either a method or a snippet.
        """
        for name, response_fields, vals in (
            ("counts", "__count total", {"json2_method": "read_group"}),
            ("summary", "branch_code", {"json2_code_snippet": "result = []"}),
        ):
            endpoint = self._create_endpoint(
                dict(vals, name=f"get_{name}", json2_response_fields=response_fields)
            )
            self.assertEqual(endpoint.json2_response_fields, response_fields)

    def test_dotted_specs_validated_whatever_the_method(self):
        """Their base must resolve against the model, method or not."""
        endpoint = self._create_endpoint(
            {
                "name": "get_counts_dotted",
                "json2_method": "read_group",
                "json2_response_fields": "__count\ncountry_id.name country",
            }
        )
        bad = ("nonexistent_id.name", "email.something", "country_id.nonexistent")
        for spec in bad:
            with self.assertRaises(ValidationError):
                endpoint.json2_response_fields = f"__count\n{spec}"

    def test_plain_names_still_validated_for_search_read(self):
        """__count is not a field of res.partner."""
        with self.assertRaises(ValidationError):
            self.endpoint.json2_response_fields = "name\n__count"

    def test_changing_method_rechecks_response_fields(self):
        """The constraint depends on json2_method, so a switch must re-run it."""
        endpoint = self._create_endpoint(
            {
                "name": "get_switched",
                "json2_method": "read_group",
                "json2_response_fields": "country_id\n__count",
            }
        )
        with self.assertRaises(ValidationError):
            endpoint.json2_method = "search_read"

    def test_empty_response_fields(self):
        self.endpoint.json2_response_fields = False
        fields, aliases = self.endpoint._json2_parse_response_fields()
        self.assertEqual(fields, [])
        self.assertEqual(aliases, {})

    def test_param_invalid_default_value(self):
        with self.assertRaises(ValidationError):
            self.env["endpoint.json2.param"].create(
                {
                    "endpoint_id": self.endpoint.id,
                    "name": "bad_param",
                    "param_type": "string",
                    "default_value": "not valid json",
                }
            )

    def test_param_bool_rejected_for_integer(self):
        param = self.env["endpoint.json2.param"].create(
            {
                "endpoint_id": self.endpoint.id,
                "name": "count",
                "param_type": "integer",
            }
        )
        self.assertFalse(param._check_param_type(True))
        self.assertFalse(param._check_param_type(False))

    def test_param_default_value_type_mismatch(self):
        with self.assertRaises(ValidationError):
            self.env["endpoint.json2.param"].create(
                {
                    "endpoint_id": self.endpoint.id,
                    "name": "bad_default",
                    "param_type": "integer",
                    "default_value": '"hello"',
                }
            )

    def test_filter_result_dict(self):
        result = {"name": "Test", "email": "a@b.c", "phone": "123"}
        filtered = self.endpoint._json2_filter_result(result, ["name", "email"])
        self.assertEqual(filtered, {"name": "Test", "email": "a@b.c"})
        aliased = self.endpoint._json2_apply_aliases(filtered, {"email": "mail"})
        self.assertEqual(aliased, {"name": "Test", "mail": "a@b.c"})

    def test_filter_result_list(self):
        result = [
            {"name": "A", "phone": "1"},
            {"name": "B", "phone": "2"},
        ]
        filtered = self.endpoint._json2_filter_result(result, ["name"])
        self.assertEqual(filtered, [{"name": "A"}, {"name": "B"}])
        aliased = self.endpoint._json2_apply_aliases(filtered, {"name": "label"})
        self.assertEqual(aliased, [{"label": "A"}, {"label": "B"}])

    def test_request_settings_constrained(self):
        with self.assertRaises(ValidationError):
            self._create_endpoint(
                {
                    "name": "get_test",
                    "request_method": "GET",
                    "json2_method": "search_read",
                }
            )
        with self.assertRaises(ValidationError):
            self._create_endpoint(
                {
                    "name": "form_test",
                    "request_content_type": "text/html",
                    "json2_method": "search_read",
                }
            )

    def test_validate_method_or_snippet_required(self):
        with self.assertRaises(ValidationError):
            self._create_endpoint({"name": "no_method_no_snippet"})

    def test_validate_snippet_without_method_ok(self):
        ep = self._create_endpoint(
            {"name": "snippet_only", "json2_code_snippet": "result = []"}
        )
        self.assertTrue(ep.json2_code_snippet)

    def test_json2_constraints_revalidated_on_write(self):
        # Both checks must stay in constraints that depend on the fields they
        # read: _check_exec_mode depends on exec_mode alone, so moving them back
        # into _validate_exec__json2 would stop catching writes.
        with self.assertRaises(ValidationError):
            self.endpoint.json2_code_snippet = "result = []"
        with self.assertRaises(ValidationError):
            self.endpoint.json2_group_ids = [Command.clear()]

    def test_dotted_response_fields_valid(self):
        self.endpoint.json2_response_fields = "name\ncountry_id.name country"
        fields, aliases = self.endpoint._json2_parse_response_fields()
        self.assertEqual(fields, ["name", "country_id.name"])
        self.assertEqual(aliases, {"country_id.name": "country"})

    def test_resolve_dotted_fields(self):
        country = self.env["res.country"].search([("code", "=", "JP")], limit=1)
        self.assertTrue(country)
        result = [
            {"id": 1, "name": "Test", "country_id": (country.id, country.display_name)},
            {"id": 2, "name": "Test2", "country_id": False},
        ]
        dotted_map = {"country_id": ["name", "code"]}
        Model = self.env["res.partner"]
        self.endpoint._json2_resolve_dotted_fields(Model, result, dotted_map)
        self.assertEqual(result[0]["country_id.name"], country.name)
        self.assertEqual(result[0]["country_id.code"], "JP")
        self.assertFalse(result[1]["country_id.name"])
        self.assertFalse(result[1]["country_id.code"])

    def test_resolve_dotted_fields_x2many(self):
        tags = self.env["res.partner.category"].search([], limit=2)
        if len(tags) < 2:
            tags = self.env["res.partner.category"].create(
                [{"name": "TagA"}, {"name": "TagB"}]
            )
        result = [
            {"id": 1, "name": "Test", "category_id": tags.ids},
            {"id": 2, "name": "Test2", "category_id": []},
        ]
        dotted_map = {"category_id": ["name"]}
        Model = self.env["res.partner"]
        self.endpoint._json2_resolve_dotted_fields(Model, result, dotted_map)
        self.assertEqual(result[0]["category_id.name"], tags.mapped("name"))
        self.assertEqual(result[1]["category_id.name"], [])

    def test_filter_excludes_base_when_only_dotted(self):
        result = {
            "name": "Test",
            "country_id": (1, "Japan"),
            "country_id.name": "Japan",
        }
        filtered = self.endpoint._json2_filter_result(
            result, ["name", "country_id.name"]
        )
        self.assertEqual(filtered, {"name": "Test", "country_id.name": "Japan"})
        self.assertNotIn("country_id", filtered)
        aliased = self.endpoint._json2_apply_aliases(
            filtered, {"country_id.name": "country"}
        )
        self.assertEqual(aliased, {"name": "Test", "country": "Japan"})

    def _encode(self, payload):
        """Encode as the controller does, through the endpoint's hook."""
        return json.loads(
            json.dumps(payload, default=self.endpoint._json2_json_default)
        )

    def test_serialize_values(self):
        encoded = self._encode(
            {
                "name": "Test",
                "write_date": datetime(2026, 1, 15, 10, 30, 0),
                "date": date(2026, 1, 15),
                # Binary fields read back base64-encoded, hence ascii.
                "avatar": base64.b64encode(b"\x89PNG"),
                # A Domain reaches the payload from any field computed with one.
                "domain": fields.Domain([("date_order", ">=", date(2026, 1, 15))]),
            }
        )
        # Datetimes carry an explicit offset so json2_tz is unambiguous;
        # everything else is left to Odoo's own encoder, at any depth.
        self.assertEqual(encoded["write_date"], "2026-01-15T10:30:00+00:00")
        self.assertEqual(encoded["date"], "2026-01-15")
        self.assertEqual(encoded["avatar"], "iVBORw==")
        self.assertEqual(encoded["domain"], [["date_order", ">=", "2026-01-15"]])

    def test_handle_exec_carries_encoder(self):
        """The hook only applies if the result hands it to the controller."""
        with MockRequest(self.env) as req:
            req.get_json_data = lambda: {}
            result = self.endpoint._handle_exec__json2(req)
        self.assertEqual(
            result["json_default"](datetime(2026, 1, 15, 10, 30, 0)),
            "2026-01-15T10:30:00+00:00",
        )
