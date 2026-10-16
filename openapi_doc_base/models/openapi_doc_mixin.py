# Copyright 2026 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import json
from types import SimpleNamespace

from odoo import api, exceptions, fields, models

from ..builder import SpecBuilder

API_DOC_FIELDS = (
    "api_doc_enabled",
    "api_doc_description",
    "api_doc_tags",
    "api_doc_input_schema",
    "api_doc_output_schema",
)


class OpenApiDocMixin(models.AbstractModel):
    """Describe records that are routes (eg: configurable endpoints).

    NOT needed to document controllers: add an `api_doc` routing key
    to the route instead. Use this mixin when routes come from records:
    it adds docs fields and turns records into rules for `SpecBuilder`.

    Implement `_openapi_route_info`.
    """

    _name = "openapi.doc.mixin"
    _description = "OpenAPI docs for route records"

    api_doc_enabled = fields.Boolean(
        string="Show in API docs",
        help="Routes are not documented by default: they might be internal.",
    )
    api_doc_description = fields.Text(string="API description")
    api_doc_tags = fields.Char(string="API tags", help="Comma separated tags.")
    api_doc_input_schema = fields.Text(
        string="Input schema", help="JSON schema of the request params or body."
    )
    api_doc_output_schema = fields.Text(
        string="Output schema", help="JSON schema of the response."
    )

    @api.constrains("api_doc_input_schema", "api_doc_output_schema")
    def _check_api_doc_schemas(self):
        """Schemas must be valid JSON objects to be used in docs."""
        for rec in self:
            for fname in ("api_doc_input_schema", "api_doc_output_schema"):
                if rec[fname] and not isinstance(rec._api_doc_schema(fname), dict):
                    raise exceptions.ValidationError(
                        self.env._(
                            "%(field)s must be a JSON object.",
                            field=rec._fields[fname].string,
                        )
                    )

    def _api_doc_schema(self, fname):
        """Parse a JSON schema field, None if empty or invalid."""
        try:
            return json.loads(self[fname]) if self[fname] else None
        except ValueError:
            return None

    @api.model_create_multi
    def create(self, vals_list):
        """Refresh docs when documented records are created."""
        records = super().create(vals_list)
        if any(vals.get("api_doc_enabled") for vals in vals_list):
            self.env.registry.clear_cache("routing")
        return records

    def write(self, vals):
        """Refresh docs when their content changes.

        Documents are cached w/ the routing map.
        """
        res = super().write(vals)
        if any(fname in vals for fname in API_DOC_FIELDS):
            self.env.registry.clear_cache("routing")
        return res

    @api.model
    def _openapi_documented_domain(self):
        """Domain of the records to document."""
        return [("api_doc_enabled", "=", True)]

    def _openapi_route_info(self):
        """Return `(route, routing)` of the record. To implement."""
        raise NotImplementedError()

    def _openapi_api_doc(self):
        """Return the `api_doc` routing key for the record."""
        tags = [t.strip() for t in (self.api_doc_tags or "").split(",") if t.strip()]
        api_doc = {
            "summary": self.display_name,
            "description": self.api_doc_description,
            "tags": tags,
            "input_schema": self._api_doc_schema("api_doc_input_schema"),
            "output_schema": self._api_doc_schema("api_doc_output_schema"),
            "operation_id": f"{self._name.replace('.', '_')}_{self.id}",
        }
        return {k: v for k, v in api_doc.items() if v}

    def _openapi_rule(self):
        """Return `(url, endpoint)` describing the record for `SpecBuilder`.

        The endpoint is a plain object holding the routing:
        the builder needs no callable.
        """
        self.ensure_one()
        route, routing = self._openapi_route_info()
        routing = dict(routing, api_doc=self._openapi_api_doc())
        return route, SimpleNamespace(routing=routing)

    def _openapi_build_doc(self, title, **kw):
        """Build the OpenAPI document of the records."""
        rules = [rec._openapi_rule() for rec in self]
        return SpecBuilder(self.env, rules, title=title, **kw).build()
