# Copyright 2026 Quartile (https://www.quartile.co)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import json
from datetime import datetime

import werkzeug

from odoo import Command, api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.service.model import get_public_method
from odoo.tools.json import json_default
from odoo.tools.safe_eval import json as safe_json
from odoo.tools.safe_eval import safe_eval, wrap_module

from odoo.addons.base.models.res_partner import _tz_get


class EndpointEndpoint(models.Model):
    _inherit = "endpoint.endpoint"

    json2_model_id = fields.Many2one(
        "ir.model",
        string="Target Model",
        ondelete="cascade",
        domain=[("transient", "=", False)],
    )
    json2_model_name = fields.Char(
        related="json2_model_id.model",
        store=True,
    )
    json2_method = fields.Char(
        string="Method",
        help="Public method name on the target model.",
    )
    json2_description = fields.Text(
        string="Description",
        help="Displayed in the API documentation endpoint.",
    )
    json2_doc_url = fields.Char(
        string="API Doc",
        compute="_compute_json2_doc_url",
    )
    json2_response_fields = fields.Text(
        string="Response Fields",
        help="One field per line. Optionally add an alias to rename in output.\n"
        "Use dotted notation (one level) for relational fields.\n"
        "Leave empty to return all fields.\n\n"
        "Examples:\n"
        "  name\n"
        "  country_id.name country\n"
        "  write_date last_modified",
    )
    json2_default_domain = fields.Char(
        string="Default Domain",
        default="[]",
        help="Default domain filter applied before calling the method (JSON format).",
    )
    json2_lang_id = fields.Many2one(
        "res.lang",
        string="Response Language",
        help="Force this language on the execution context so that translatable "
        "field values (including dotted relational fields) are returned in it, "
        "regardless of the API user's language.",
    )
    json2_tz = fields.Selection(
        _tz_get,
        string="Response Timezone",
        help="Render datetime values in the response in this timezone. Values are "
        "always ISO 8601 with a UTC offset (e.g. 2026-07-27T13:30:00+09:00), so "
        "this only selects the offset they carry. Leave empty to render in UTC. "
        "Incoming datetime parameters are not converted.",
    )
    json2_group_ids = fields.Many2many(
        "res.groups",
        string="Allowed Groups",
        help="Groups allowed to call this endpoint.",
    )
    json2_param_ids = fields.One2many(
        "endpoint.json2.param",
        "endpoint_id",
        string="Parameters",
    )
    json2_code_snippet = fields.Text(
        string="JSON-2 Code Snippet",
        help="Optional Python code executed instead of the model method. "
        "Available variables: Model, params, env, Command, json, exceptions, log. "
        "Use record.write({...}) for updates. "
        "Set the result in the 'result' variable.",
    )

    def _selection_exec_mode(self):
        return super()._selection_exec_mode() + [("json2", "JSON-2 API")]

    @api.depends("exec_mode", "route_group", "name")
    def _compute_route(self):
        super()._compute_route()
        for rec in self:
            if rec.exec_mode == "json2" and rec.route_group and rec.name:
                rec.route = f"/json2/{rec.route_group}/{rec.name}"
        return

    @api.depends("exec_mode", "route_group")
    def _compute_json2_doc_url(self):
        base = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "")
        for rec in self:
            if rec.exec_mode == "json2" and rec.route_group:
                rec.json2_doc_url = f"{base}/json2/doc/{rec.route_group}"
            else:
                rec.json2_doc_url = False

    @api.onchange("exec_mode")
    def _onchange_exec_mode_json2_defaults(self):
        if self.exec_mode == "json2":
            self.request_method = "POST"
            self.request_content_type = "application/json"

    def _validate_exec__json2(self):
        if not self.json2_model_id:
            raise ValidationError(
                self.env._("Exec mode is set to 'JSON-2 API': you must select a model.")
            )

    @api.constrains("exec_mode", "json2_method", "json2_code_snippet")
    def _check_json2_exec_target(self):
        for rec in self:
            if rec.exec_mode != "json2":
                continue
            if not rec.json2_method and not rec.json2_code_snippet:
                raise ValidationError(
                    self.env._(
                        "Exec mode is set to 'JSON-2 API': you must specify a "
                        "method or provide a code snippet."
                    )
                )
            if rec.json2_method and rec.json2_code_snippet:
                raise ValidationError(
                    self.env._(
                        "A JSON-2 API endpoint runs either a method or a code snippet, "
                        "not both: leave one of them empty."
                    )
                )

    @api.constrains("exec_mode", "json2_group_ids")
    def _check_json2_group_ids(self):
        for rec in self:
            if rec.exec_mode == "json2" and not rec.json2_group_ids:
                raise ValidationError(
                    self.env._(
                        "A JSON-2 API endpoint must allow at least one group: with an "
                        "empty list, every caller is denied."
                    )
                )

    @api.constrains("request_method", "request_content_type", "exec_mode")
    def _check_json2_request_settings(self):
        for rec in self:
            if rec.exec_mode != "json2":
                continue
            if (
                rec.request_method != "POST"
                or rec.request_content_type != "application/json"
            ):
                raise ValidationError(
                    self.env._(
                        "JSON-2 API endpoints must use POST with 'application/json' "
                        "content type."
                    )
                )

    @api.constrains("json2_method")
    def _check_json2_method(self):
        for rec in self:
            if rec.json2_method and rec.json2_method.startswith("_"):
                raise ValidationError(
                    self.env._("Private methods (starting with '_') cannot be exposed.")
                )

    @api.constrains("json2_default_domain")
    def _check_json2_default_domain(self):
        for rec in self:
            if not rec.json2_default_domain:
                continue
            try:
                domain = json.loads(rec.json2_default_domain)
                if not isinstance(domain, list):
                    raise ValueError
            except (json.JSONDecodeError, ValueError):
                raise ValidationError(
                    self.env._("Default domain must be a valid JSON list.")
                ) from None

    def _json2_is_valid_response_field(self, Model, field_spec):
        if "." not in field_spec:
            return field_spec in Model._fields
        base, sub = field_spec.split(".", 1)
        fd = Model._fields.get(base)
        return (
            fd
            and fd.type in ("many2one", "many2many", "one2many")
            and sub in self.env[fd.comodel_name]._fields
        )

    @api.constrains("json2_response_fields", "json2_model_id", "json2_method")
    def _check_json2_response_fields(self):
        for rec in self:
            if not rec.json2_response_fields or not rec.json2_model_name:
                continue
            if rec.json2_model_name not in self.env:
                continue
            Model = self.env[rec.json2_model_name]
            field_names, _aliases = rec._json2_parse_response_fields()
            # Plain names are checked only for these two methods. This is a
            # policy choice, not a taxonomy of the ORM: read_group returns model
            # field values too and is deliberately excluded, because its rows
            # carry keys of its own (__count, __domain) as well. A module wanting
            # its own method checked should constrain it where the payload is
            # defined, which can pin the exact keys rather than merely "is a
            # field of the model".
            # Dotted specs stay checkable whatever the method is, because
            # _json2_resolve_dotted_fields resolves their base against
            # Model._fields before injecting the related values.
            reads_fields = rec.json2_method in ("read", "search_read")
            invalid = [
                f
                for f in field_names
                if ("." in f or reads_fields)
                and not rec._json2_is_valid_response_field(Model, f)
            ]
            if invalid:
                raise ValidationError(
                    self.env._(
                        "Invalid field(s) for %(model)s: %(fields)s",
                        model=rec.json2_model_name,
                        fields=", ".join(invalid),
                    )
                )

    def _json2_check_group_access(self, request):
        if not (self.json2_group_ids & request.env.user.all_group_ids):
            raise werkzeug.exceptions.Forbidden(
                "User does not belong to any allowed group"
            )

    def _json2_validate_params(self, kwargs):
        params = {}
        for param_def in self.json2_param_ids:
            params[param_def.name] = param_def._extract_value(
                kwargs.pop(param_def.name, None)
            )
        return params

    def _json2_get_code_snippet_eval_context(self, Model, params):
        return {
            "Model": Model,
            "params": params,
            "env": Model.env,
            "Command": Command,
            "json": safe_json,
            "exceptions": wrap_module(
                werkzeug.exceptions,
                [
                    "BadRequest",
                    "Forbidden",
                    "NotFound",
                    "UnprocessableEntity",
                    "InternalServerError",
                ],
            ),
            "log": self._code_snippet_log_func,
        }

    def _json2_exec_code_snippet(self, Model, params):
        eval_ctx = self._json2_get_code_snippet_eval_context(Model, params)
        safe_eval(self.json2_code_snippet, eval_ctx, mode="exec")
        if "result" not in eval_ctx:
            raise werkzeug.exceptions.InternalServerError(
                "Code snippet must set a 'result' variable."
            )
        return eval_ctx["result"]

    def _json2_parse_response_fields(self):
        """Parse response fields text into a field list and alias map.

        Returns (fields, aliases) where aliases maps field_name -> alias.
        """
        self.ensure_one()
        if not self.json2_response_fields:
            return [], {}
        field_list = []
        aliases = {}
        for line in self.json2_response_fields.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            field_list.append(parts[0])
            if len(parts) > 1:
                aliases[parts[0]] = parts[1]
        return field_list, aliases

    def _json2_parse_dotted_fields(self, response_fields):
        dotted = {}
        for f in response_fields:
            if "." in f:
                base, sub = f.split(".", 1)
                dotted.setdefault(base, []).append(sub)
        return dotted

    def _json2_extract_rel_ids(self, val):
        """Extract record IDs from search_read relational field values."""
        if not val:
            return []
        if isinstance(val, int):
            return [val]
        if isinstance(val, (list, tuple)):
            if val and isinstance(val[0], int):
                if len(val) == 2 and isinstance(val[1], str):
                    return [val[0]]
                return list(val)
        if isinstance(val, dict):
            rec_id = val.get("id")
            return [rec_id] if rec_id else []
        return []

    def _json2_normalize_rows(self, result):
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return [result]
        return []

    def _json2_collect_rel_ids(self, rows, base_field):
        all_ids = set()
        rel_ids_map = []
        for row in rows:
            if isinstance(row, dict):
                rel_ids = self._json2_extract_rel_ids(row.get(base_field))
            else:
                rel_ids = []
            rel_ids_map.append(rel_ids)
            all_ids.update(rel_ids)
        return all_ids, rel_ids_map

    def _json2_fetch_related(self, Model, field_def, ids, sub_fields):
        if not ids:
            return {}
        comodel = Model.env[field_def.comodel_name]
        return {
            r["id"]: r
            for r in comodel.search_read([("id", "in", list(ids))], fields=sub_fields)
        }

    def _json2_inject_dotted_values(
        self, rows, base_field, sub_fields, related, is_x2many, rel_ids_map
    ):
        for row, rel_ids in zip(rows, rel_ids_map, strict=False):
            if not isinstance(row, dict):
                continue
            if is_x2many:
                recs = [related[i] for i in rel_ids if i in related]
                for sub in sub_fields:
                    row[f"{base_field}.{sub}"] = [r.get(sub, False) for r in recs]
            else:
                rec = related.get(rel_ids[0], {}) if rel_ids else {}
                for sub in sub_fields:
                    row[f"{base_field}.{sub}"] = rec.get(sub, False)

    def _json2_resolve_dotted_fields(self, Model, result, dotted_map):
        # rows shares references with result; mutations propagate back.
        rows = self._json2_normalize_rows(result)
        if not rows:
            return result
        for base_field, sub_fields in dotted_map.items():
            field_def = Model._fields.get(base_field)
            if not field_def or field_def.type not in (
                "many2one",
                "many2many",
                "one2many",
            ):
                continue
            ids, rel_ids_map = self._json2_collect_rel_ids(rows, base_field)
            related = self._json2_fetch_related(Model, field_def, ids, sub_fields)
            self._json2_inject_dotted_values(
                rows,
                base_field,
                sub_fields,
                related,
                is_x2many=field_def.type != "many2one",
                rel_ids_map=rel_ids_map,
            )
        return result

    def _json2_filter_result(self, result, response_fields):
        if not response_fields:
            return result
        field_set = set(response_fields)
        if isinstance(result, list):
            return [
                {k: v for k, v in row.items() if k in field_set}
                if isinstance(row, dict)
                else row
                for row in result
            ]
        if isinstance(result, dict):
            return {k: v for k, v in result.items() if k in field_set}
        return result

    def _json2_apply_aliases(self, result, aliases):
        def _rename(row):
            if not isinstance(row, dict):
                return row
            return {aliases.get(k, k): v for k, v in row.items()}

        if isinstance(result, list):
            return [_rename(row) for row in result]
        if isinstance(result, dict):
            return _rename(result)
        return result

    def _json2_json_default(self, val):
        """Encoder hook for values json cannot represent.

        json.dumps applies this at every depth, so nested values are covered
        without walking the payload ourselves.
        """
        if isinstance(val, datetime):
            # Render as ISO-8601 with an explicit offset, pinning the timezone
            # (UTC when unset) so it does not silently follow the API user's.
            # json_default would give naive UTC, which cannot carry json2_tz.
            record = self.with_context(tz=self.json2_tz or "UTC")
            return fields.Datetime.context_timestamp(record, val).isoformat()
        return json_default(val)

    def _handle_exec__json2(self, request):
        self._json2_check_group_access(request)
        kwargs = request.get_json_data() or {}
        params = self._json2_validate_params(kwargs)
        Model = request.env[self.json2_model_name].sudo()
        if self.json2_lang_id:
            Model = Model.with_context(lang=self.json2_lang_id.code)
        if self.json2_tz:
            Model = Model.with_context(tz=self.json2_tz)
        default_domain = json.loads(self.json2_default_domain or "[]")
        if default_domain:
            params["domain"] = default_domain + (params.get("domain") or [])
        response_fields, aliases = self._json2_parse_response_fields()
        dotted_map = self._json2_parse_dotted_fields(response_fields)
        if dotted_map and params.get("fields"):
            params["fields"] = list(set(params["fields"]) | dotted_map.keys())
        if self.json2_code_snippet:
            result = self._json2_exec_code_snippet(Model, params)
        else:
            try:
                method = get_public_method(Model, self.json2_method)
            except (AttributeError, AccessError) as exc:
                raise werkzeug.exceptions.NotFound(str(exc)) from exc
            result = method(Model, **params)
        if dotted_map:
            result = self._json2_resolve_dotted_fields(Model, result, dotted_map)
        result = self._json2_filter_result(result, response_fields)
        if aliases:
            result = self._json2_apply_aliases(result, aliases)
        return {"payload": result, "json_default": self._json2_json_default}
