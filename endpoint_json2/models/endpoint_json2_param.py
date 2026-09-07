# Copyright 2026 Quartile (https://www.quartile.co)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import json

import werkzeug

from odoo import api, fields, models
from odoo.exceptions import ValidationError

PARAM_TYPE_MAP = {
    "string": str,
    "integer": int,
    "float": float,
    "boolean": bool,
    "list": list,
    "dict": dict,
}


class EndpointJson2Param(models.Model):
    _name = "endpoint.json2.param"
    _description = "JSON2 Endpoint Parameter"
    _order = "sequence, id"

    endpoint_id = fields.Many2one(
        "endpoint.endpoint",
        required=True,
        ondelete="cascade",
    )
    name = fields.Char(required=True, help="Parameter name as sent in the JSON body.")
    description = fields.Char(help="Displayed in the API documentation.")
    param_type = fields.Selection(
        [
            ("string", "String"),
            ("integer", "Integer"),
            ("float", "Float"),
            ("boolean", "Boolean"),
            ("list", "List"),
            ("dict", "Dict"),
        ],
        string="Type",
        required=True,
        default="string",
    )
    required = fields.Boolean()
    default_value = fields.Char(
        help="Default value (JSON-encoded) when the parameter is not provided.",
    )
    sequence = fields.Integer(default=10)

    def _check_param_type(self, value):
        self.ensure_one()
        expected_type = PARAM_TYPE_MAP.get(self.param_type)
        if not expected_type:
            return True
        if isinstance(value, bool) and expected_type is not bool:
            return False
        if expected_type is float:
            return isinstance(value, (int, float))
        return isinstance(value, expected_type)

    def _extract_value(self, raw_value):
        self.ensure_one()
        value = raw_value
        if value is None and self.default_value:
            value = json.loads(self.default_value)
        if value is None and self.required:
            raise werkzeug.exceptions.UnprocessableEntity(
                f"Missing required parameter: {self.name}"
            )
        if value is not None and not self._check_param_type(value):
            raise werkzeug.exceptions.UnprocessableEntity(
                f"Parameter {self.name!r} must be of type {self.param_type}"
            )
        return value

    @api.constrains("default_value", "param_type")
    def _check_default_value(self):
        for rec in self:
            if not rec.default_value:
                continue
            try:
                parsed = json.loads(rec.default_value)
            except json.JSONDecodeError:
                raise ValidationError(
                    self.env._(
                        "Default value must be valid JSON: %(value)s",
                        value=rec.default_value,
                    )
                ) from None
            if not rec._check_param_type(parsed):
                raise ValidationError(
                    self.env._(
                        "Default value type mismatch: expected %(type)s",
                        type=rec.param_type,
                    )
                ) from None
