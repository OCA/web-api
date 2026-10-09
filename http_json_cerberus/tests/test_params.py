# Copyright 2026 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from types import SimpleNamespace

from cerberus import Validator

from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger

from odoo.addons.http_json_dispatcher.errors import ApiValidationError

from ..params import CerberusParam

SCHEMA = {
    "name": {"type": "string", "required": True},
    "qty": {"type": "integer", "coerce": int},
}


class Owner:
    calls = 0

    def _get_schema(self):
        Owner.calls += 1
        return SCHEMA


class TestCerberusParam(TransactionCase):
    def _ctx(self, owner=None):
        return SimpleNamespace(env=self.env, owner=owner)

    def test_input(self):
        """Input is validated and coerced; unknown keys are dropped."""
        param = CerberusParam(SCHEMA)
        res = param.from_params(self._ctx(), {"name": "a", "qty": "2", "x": 1})
        self.assertEqual(res, {"name": "a", "qty": 2})

    def test_input_error(self):
        """Missing required keys raise an error w/ the Cerberus errors."""
        param = CerberusParam(SCHEMA)
        with self.assertRaises(ApiValidationError) as err:
            param.from_params(self._ctx(), {"qty": 1})
        self.assertEqual(
            err.exception.rest_json_info, {"errors": {"name": ["required field"]}}
        )
        self.assertIn("BadRequest", str(err.exception))

    def test_keep_unknown(self):
        """With `purge_unknown=False`, unknown keys are an error."""
        param = CerberusParam(SCHEMA, purge_unknown=False)
        with self.assertRaises(ApiValidationError):
            param.from_params(self._ctx(), {"name": "a", "x": 1})

    def test_output(self):
        """Output follows the schema; invalid output raises a SystemError."""
        param = CerberusParam(SCHEMA)
        self.assertEqual(param.to_response(self._ctx(), {"name": "a"}), {"name": "a"})
        with self.assertRaises(SystemError):
            param.to_response(self._ctx(), {"qty": 1})

    @mute_logger("odoo.addons.http_json_cerberus.params")
    def test_output_not_strict(self):
        """With `strict_output=False`, invalid output is returned as is."""
        param = CerberusParam(SCHEMA, strict_output=False)
        self.assertEqual(param.to_response(self._ctx(), {"qty": 1}), {"qty": 1})

    def test_schema_lookup(self):
        """The schema can be a method name, a callable or a Validator."""
        Owner.calls = 0
        param = CerberusParam("_get_schema")
        ctx = self._ctx(owner=Owner())
        self.assertEqual(param.from_params(ctx, {"name": "a"}), {"name": "a"})
        param.from_params(ctx, {"name": "a"})
        self.assertEqual(Owner.calls, 2)
        param = CerberusParam(lambda ctx, direction: SCHEMA)
        self.assertEqual(param.from_params(ctx, {"name": "a"}), {"name": "a"})
        param = CerberusParam(Validator(SCHEMA, purge_unknown=True))
        self.assertEqual(param.from_params(ctx, {"name": "a"}), {"name": "a"})

    def test_schema_cache(self):
        """With `cache=True`, the schema method is looked up once per direction."""
        Owner.calls = 0
        param = CerberusParam("_get_schema", cache=True)
        ctx = self._ctx(owner=Owner())
        param.from_params(ctx, {"name": "a"})
        param.from_params(ctx, {"name": "b"})
        self.assertEqual(Owner.calls, 1)
        param.to_response(ctx, {"name": "b"})
        self.assertEqual(Owner.calls, 2)

    def test_list(self):
        """`as_list` validates each item and the min/max number of items."""
        param = CerberusParam(SCHEMA, as_list=True, min_items=1, max_items=2)
        ctx = self._ctx()
        self.assertEqual(
            param.to_response(ctx, [{"name": "a", "x": 1}, {"name": "b"}]),
            [{"name": "a"}, {"name": "b"}],
        )
        with self.assertRaises(SystemError):
            param.to_response(ctx, [])
        with self.assertRaises(ApiValidationError) as err:
            param.from_params(ctx, [{"name": "a"}, {"qty": 1}, {"name": "c"}])
        self.assertEqual(
            err.exception.rest_json_info["errors"],
            {1: {"name": ["required field"]}, "max_items": ["3 > 2"]},
        )

    def test_json_schema(self):
        """The schema is converted to the JSON schema of a list of objects."""
        param = CerberusParam(SCHEMA, as_list=True, min_items=1, unique_items=True)
        self.assertEqual(
            param.to_json_schema(self._ctx(), "output"),
            {
                "type": "array",
                "minItems": 1,
                "uniqueItems": True,
                "items": {
                    "type": "object",
                    "required": ["name"],
                    "properties": {
                        "name": {"type": "string"},
                        "qty": {"type": "integer"},
                    },
                },
            },
        )
