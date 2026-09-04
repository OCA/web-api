# Copyright 2021 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import json
import symtable
import textwrap

import jsonschema
import werkzeug
import yaml
from lxml import etree

from odoo import api, exceptions, fields, http, models
from odoo.exceptions import UserError
from odoo.tools import safe_eval

from odoo.addons.rpc_helper.decorator import disable_rpc

from ..exceptions import RequestValidationError

hashlib = safe_eval.wrap_module(
    __import__("hashlib"),
    [
        "sha1",
        "sha224",
        "sha256",
        "sha384",
        "sha512",
        "sha3_224",
        "sha3_256",
        "sha3_384",
        "sha3_512",
        "shake_128",
        "shake_256",
        "blake2b",
        "blake2s",
        "md5",
        "new",
    ],
)
hmac = safe_eval.wrap_module(
    __import__("hmac"),
    ["new", "compare_digest"],
)

# ``safe_eval`` injects these built-ins at runtime. Keep validation aligned with
# Odoo instead of maintaining a second, potentially outdated list here.
_SAFE_EVAL_BUILTINS = frozenset(safe_eval._BUILTINS)


@disable_rpc()  # Block ALL RPC calls
class EndpointMixin(models.AbstractModel):
    _name = "endpoint.mixin"
    _inherit = "endpoint.route.handler"
    _description = "Endpoint mixin"

    exec_mode = fields.Selection(
        selection="_selection_exec_mode",
        required=True,
    )
    request_content_schema = fields.Text(
        help=(
            "Optional schema validated against the parsed request body. "
            "The accepted format depends on 'Request content type':\n"
            " - application/json: JSON Schema (Draft 2020-12), as YAML or JSON\n"
            " - application/xml, text/xml: XML Schema (XSD)\n"
            "If empty, no validation runs."
        ),
    )
    request_content_schema_applicable = fields.Boolean(
        compute="_compute_request_content_schema_applicable",
    )
    code_snippet = fields.Text()
    code_snippet_docs = fields.Text(
        compute="_compute_code_snippet_docs",
        default=lambda self: self._default_code_snippet_docs(),
    )
    exec_as_user_id = fields.Many2one(comodel_name="res.users")
    company_id = fields.Many2one("res.company", string="Company")

    def _selection_exec_mode(self):
        return [("code", "Execute code")]

    def _compute_code_snippet_docs(self):
        for rec in self:
            rec.code_snippet_docs = textwrap.dedent(rec._default_code_snippet_docs())

    @api.constrains("exec_mode")
    def _check_exec_mode(self):
        for rec in self:
            rec._validate_exec_mode()

    def _validate_exec_mode(self):
        validator = getattr(self, "_validate_exec__" + self.exec_mode, lambda: True)
        validator()

    def _validate_exec__code(self):
        if not self._code_snippet_valued():
            raise UserError(
                self.env._(
                    "Exec mode is set to `Code`: you must provide a piece of code"
                )
            )

    def _registry_sync_errors(self):
        errors = super()._registry_sync_errors()
        snippet = self.code_snippet or ""
        syntax_error = safe_eval.test_python_expr(snippet, mode="exec")
        if syntax_error:
            errors.append(
                self.env._("Invalid code snippet: %(error)s", error=syntax_error)
            )
            return errors

        unavailable_names = self._code_snippet_unavailable_names(snippet)
        if unavailable_names:
            errors.append(
                self.env._(
                    "The code snippet uses unavailable variable(s): %(names)s. "
                    "Available system variables are: %(available_names)s.",
                    names=", ".join(unavailable_names),
                    available_names=", ".join(
                        sorted(self._code_snippet_system_variable_names())
                    ),
                )
            )
        return errors

    def _code_snippet_system_variable_names(self):
        # Derive names from the actual evaluation context so this validation
        # stays accurate when another system variable is added.
        return set(self._get_code_snippet_eval_context(request=None))

    def _code_snippet_unavailable_names(self, snippet):
        """Find global names that safe_eval will not provide at runtime."""
        symbol_table = symtable.symtable(snippet, "<endpoint>", "exec")
        referenced_globals = set()

        # ``symtable`` distinguishes global lookups from local names in nested
        # functions and comprehensions, avoiding warnings for valid variables.
        def collect_globals(table):
            for symbol in table.get_symbols():
                if symbol.is_referenced() and symbol.is_global():
                    referenced_globals.add(symbol.get_name())
            for child in table.get_children():
                collect_globals(child)

        collect_globals(symbol_table)
        assigned_names = {
            symbol.get_name()
            for symbol in symbol_table.get_symbols()
            if symbol.is_assigned() or symbol.is_imported()
        }
        available_names = (
            self._code_snippet_system_variable_names()
            | _SAFE_EVAL_BUILTINS
            | assigned_names
        )
        return sorted(referenced_globals - available_names)

    def _get_request_content_schema_applicable_for_types(self):
        """Content types for which ``request_content_schema`` applies."""
        return ["application/json", "application/xml"]

    @api.depends("request_method", "request_content_type")
    def _compute_request_content_schema_applicable(self):
        applicable_types = self._get_request_content_schema_applicable_for_types()
        for rec in self:
            rec.request_content_schema_applicable = (
                rec.request_method in ("POST", "PUT")
                and rec.request_content_type in applicable_types
            )

    @api.onchange("request_content_type")
    def _onchange_request_content_type_clear_schema(self):
        # The schema format depends on the content type (e.g. JSON Schema vs
        # XSD), so it cannot survive a content type change.
        self.request_content_schema = False

    @api.constrains("request_content_schema", "request_content_type")
    def _check_request_content_schema(self):
        for rec in self:
            if not rec.request_content_schema:
                continue
            elif rec.request_content_type == "application/json":
                rec._check_request_content_schema_json()
            elif rec.request_content_type == "application/xml":
                rec._check_request_content_schema_xml()

    def _check_request_content_schema_json(self):
        try:
            schema = yaml.safe_load(self.request_content_schema)
        except yaml.YAMLError as exception:
            raise UserError(
                self.env._("Invalid YAML/JSON in request content schema: %s", exception)
            ) from exception
        try:
            jsonschema.Draft202012Validator.check_schema(schema)
        except jsonschema.SchemaError as exception:
            raise UserError(
                self.env._(
                    "Invalid JSON Schema in request content schema: %s",
                    exception.message,
                )
            ) from exception

    def _check_request_content_schema_xml(self):
        try:
            schema_doc = etree.fromstring(self.request_content_schema.encode())
        except etree.XMLSyntaxError as exception:
            raise UserError(
                self.env._("Invalid XML in request content schema: %s", exception)
            ) from exception
        try:
            etree.XMLSchema(schema_doc)
        except etree.XMLSchemaParseError as exception:
            raise UserError(
                self.env._(
                    "Invalid XML Schema (XSD) in request content schema: %s",
                    exception,
                )
            ) from exception

    @api.constrains("auth_type")
    def _check_auth(self):
        for rec in self:
            if rec.auth_type == "public" and not rec.exec_as_user_id:
                raise UserError(
                    self.env._("'Exec as user' is mandatory for public endpoints.")
                )

    def _default_code_snippet_docs(self):
        return """
        Available vars:

        * env
        * endpoint
        * request
        * datetime
        * dateutil
        * time
        * user
        * json
        * Response
        * werkzeug
        * exceptions
        * hashlib: Python 'hashlib' library. Available methods:
            'sha1', 'sha224', 'sha256',
            'sha384', 'sha512', 'sha3_224', 'sha3_256', 'sha3_384',
            'sha3_512', 'shake_128', 'shake_256', 'blake2b',
            'blake2s', 'md5', 'new'
        * hmac: Python 'hmac' library. Use 'new' to create HMAC objects.

        Must generate either an instance of ``Response`` into ``response`` var or:

        * payload
        * headers
        * status_code

        which are all optional.

        Use ``log`` function to log messages into ir.logging table.
        """

    def _get_code_snippet_eval_context(self, request):
        """Prepare the context used when evaluating python code

        :returns: dict -- evaluation context given to safe_eval
        """
        return {
            "env": self.env,
            "user": self.env.user,
            "endpoint": self,
            "request": request,
            "datetime": safe_eval.datetime,
            "dateutil": safe_eval.dateutil,
            "time": safe_eval.time,
            "json": safe_eval.json,
            "Response": http.Response,
            "werkzeug": safe_eval.wrap_module(
                werkzeug, {"exceptions": ["NotFound", "BadRequest", "Unauthorized"]}
            ),
            "exceptions": safe_eval.wrap_module(
                exceptions, ["UserError", "ValidationError"]
            ),
            "log": self._code_snippet_log_func,
            "hmac": hmac,
            "hashlib": hashlib,
        }

    def _code_snippet_log_func(self, message, level="info"):
        # Almost barely copied from ir.actions.server
        with self.pool.cursor() as cr:
            cr.execute(
                """
                INSERT INTO ir_logging
                (
                    create_date,
                    create_uid,
                    type,
                    dbname,
                    name,
                    level,
                    message,
                    path,
                    line,
                    func
                )
                VALUES (
                    NOW() at time zone 'UTC',
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    self.env.uid,
                    "server",
                    self.env.cr.dbname,
                    __name__,
                    level,
                    message,
                    "endpoint",
                    self.id,
                    self.name,
                ),
            )

    def _handle_exec__code(self, request):
        if not self._code_snippet_valued():
            return {}
        eval_ctx = self._get_code_snippet_eval_context(request)
        snippet = self.code_snippet
        safe_eval.safe_eval(snippet, eval_ctx, mode="exec")
        result = eval_ctx.get("result")
        if not isinstance(result, dict):
            raise exceptions.UserError(
                self.env._("code_snippet should return a dict into `result` variable.")
            )
        return result

    def _code_snippet_valued(self):
        snippet = self.code_snippet or ""
        return bool(
            [
                not line.startswith("#")
                for line in (snippet.splitlines())
                if line.strip("")
            ]
        )

    def _default_endpoint_options_handler(self):
        kdp = "odoo.addons.endpoint.controllers.main.EndpointController"
        return {
            "klass_dotted_path": kdp,
            "method_name": "auto_endpoint",
            "default_pargs": (self._name, self.route),
        }

    def _validate_request(self, request):
        http_req = request.httprequest
        if self.request_method and self.request_method != http_req.method:
            self._logger.error("_validate_request: MethodNotAllowed")
            raise werkzeug.exceptions.MethodNotAllowed()
        if (
            self.request_content_type
            and self.request_content_type != http_req.content_type
        ):
            self._logger.error("_validate_request: UnsupportedMediaType")
            raise werkzeug.exceptions.UnsupportedMediaType()
        self._validate_request_content(request)

    def _validate_request_content(self, request):
        if not (self.request_content_schema and self.request_content_schema_applicable):
            return
        if self.request_content_type == "application/json":
            self._validate_request_content_json(request)
        elif self.request_content_type == "application/xml":
            self._validate_request_content_xml(request)

    def _validate_request_content_json(self, request):
        try:
            body = request.get_json_data()
        except json.JSONDecodeError as exception:
            self._logger.error("Invalid JSON body: %s", exception)
            raise RequestValidationError(
                [{"loc": ["body"], "msg": str(exception), "type": "json_invalid"}]
            ) from exception
        schema = yaml.safe_load(self.request_content_schema)
        errors = list(jsonschema.Draft202012Validator(schema).iter_errors(body))
        if errors:
            self._logger.error("Schema validation failed (%d errors)", len(errors))
            raise RequestValidationError(
                [
                    {
                        "loc": ["body", *err.absolute_path],
                        "msg": err.message,
                        "type": err.validator,
                    }
                    for err in errors
                ]
            )

    def _validate_request_content_xml(self, request):
        body = request.httprequest.get_data()
        try:
            doc = etree.fromstring(body)
        except etree.XMLSyntaxError as exception:
            self._logger.error("Invalid XML body: %s", exception)
            raise RequestValidationError(
                [{"loc": ["body"], "msg": str(exception), "type": "xml_invalid"}]
            ) from exception
        schema = etree.XMLSchema(etree.fromstring(self.request_content_schema.encode()))
        if not schema.validate(doc):
            self._logger.error(
                "Schema validation failed (%d errors)", len(schema.error_log)
            )
            raise RequestValidationError(
                [
                    {"loc": ["body"], "msg": err.message, "type": "xml_schema"}
                    for err in schema.error_log
                ]
            )

    def _get_handler(self):
        try:
            return getattr(self, "_handle_exec__" + self.exec_mode)
        except AttributeError as e:
            raise UserError(
                self.env._("Missing handler for exec mode %s", self.exec_mode)
            ) from e

    def _handle_request(self, request):
        # Switch user for the whole process
        self_with_user = self
        if self.exec_as_user_id:
            self_with_user = self.with_user(user=self.exec_as_user_id)
        handler = self_with_user._get_handler()
        try:
            res = handler(request)
        except self._bad_request_exceptions() as orig_exec:
            self._logger.error("_validate_request: BadRequest")
            raise werkzeug.exceptions.BadRequest() from orig_exec
        return res

    def _bad_request_exceptions(self):
        return (exceptions.UserError, exceptions.ValidationError)

    @api.model
    def _find_endpoint(self, endpoint_route):
        return self.sudo().search(self._find_endpoint_domain(endpoint_route), limit=1)

    def _find_endpoint_domain(self, endpoint_route):
        return [("route", "=", endpoint_route)]

    def copy_data(self, default=None):
        # OVERRIDE: ``route`` cannot be copied as it must me unique.
        # Yet, we want to be able to duplicate a record from the UI.
        self.ensure_one()
        default = dict(default or {})
        default.setdefault("route", f"{self.route}/COPY_FIXME")
        return super().copy_data(default=default)
