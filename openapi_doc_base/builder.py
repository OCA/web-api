# Copyright 2018 ACSONE SA/NV
# Copyright 2026 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
"""Build OpenAPI documents from routes.

Heavily inspired by the apispec plugins of `base_rest` (OCA/rest-framework):
default responses and the conversion of input schemas
to query parameters come from there.

The builder takes `(url, endpoint)` pairs as input,
whatever their origin: the routing map, a routes generator, a list of records.
`endpoint` can be any object w/ a `routing` dict (it does not need to be callable).
Everything is read from the routing:

* methods, auth
* `input` / `output` params: any object w/ `to_json_schema(ctx, direction)`
* `api_doc`: `summary`, `description`, `tags`, `operation_id`, `deprecated`,
  `exclude`, `input_schema`, `output_schema` (plain JSON schemas,
  used when there are no params), `content_type` (of the request body)
"""

import dataclasses
import inspect
import logging
import re
from typing import Any

_logger = logging.getLogger(__name__)

OPENAPI_VERSION = "3.0.3"
# werkzeug rule placeholders: `<name>`, `<int:name>`, `<model("res.partner"):name>`
PATH_PARAM_RE = re.compile(r"<(?:(?P<converter>\w+)(?:\([^)]*\))?:)?(?P<name>\w+)>")
CONVERTER_SCHEMAS = {
    "int": {"type": "integer"},
    "float": {"type": "number"},
    "uuid": {"type": "string", "format": "uuid"},
    # Odoo converters: record id(s)
    "model": {"type": "integer"},
    "models": {"type": "string"},
}
QUERY_METHODS = ("GET", "DELETE", "HEAD")
IGNORED_METHODS = ("OPTIONS", "HEAD")
DEFAULT_METHODS = ("GET", "POST")
DEFAULT_RESPONSES = {
    "400": {"description": "One of the given parameter is not valid"},
    "401": {"description": "The user is not authorized. Authentication is required"},
    "403": {
        "description": "You don't have the permission to access "
        "the requested resource."
    },
    "404": {"description": "Requested resource not found"},
}


@dataclasses.dataclass
class DocContext:
    """Context passed to params when generating docs (no request)."""

    env: Any
    endpoint: Any
    owner: Any = None


def openapi_path(url):
    """Convert a werkzeug route to an OpenAPI path and its path params."""
    params = []
    for match in PATH_PARAM_RE.finditer(url):
        schema = CONVERTER_SCHEMAS.get(match.group("converter"), {"type": "string"})
        params.append(
            {
                "name": match.group("name"),
                "in": "path",
                "required": True,
                "schema": dict(schema),
            }
        )
    return PATH_PARAM_RE.sub(r"{\g<name>}", url), params


def schema_to_query_parameters(json_schema):
    """Turn the properties of an object schema into query parameters."""
    required = json_schema.get("required") or []
    params = []
    for name, prop in (json_schema.get("properties") or {}).items():
        param = {
            "name": name,
            "in": "query",
            "required": name in required,
            "schema": dict(prop),
        }
        if "description" in prop:
            param["description"] = prop["description"]
        params.append(param)
    return params


def schema_to_request_body(json_schema, content_type="application/json"):
    """Wrap a JSON schema as request body."""
    return {"content": {content_type: {"schema": json_schema}}}


def schema_to_response(json_schema, description="Success"):
    """Wrap a JSON schema as JSON response, if any."""
    res = {"description": description}
    if json_schema:
        res["content"] = {"application/json": {"schema": json_schema}}
    return res


def _slug(value):
    """Make a valid operation id from any string."""
    return re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_")


class SpecBuilder:
    """Build an OpenAPI document for the given routes.

    :param env: Odoo env
    :param rules: iterable of `(url, endpoint)`
    :param title: title of the document
    :param version: version of the API
    :param description: description of the API
    :param servers: list of OpenAPI server objects
    :param parameters: extra parameters added to all operations (eg: headers)
    """

    def __init__(
        self,
        env,
        rules,
        title,
        version="1.0",
        description=None,
        servers=None,
        parameters=None,
    ):
        """Keep the inputs: nothing is computed until `build`."""
        self.env = env
        self.rules = rules
        self.title = title
        self.version = version
        self.description = description
        self.servers = servers
        self.parameters = list(parameters or [])
        self.ir_http = env["ir.http"]

    def build(self):
        """Return the OpenAPI document as a dict."""
        spec = {
            "openapi": OPENAPI_VERSION,
            "info": {"title": self.title, "version": self.version},
            "paths": {},
            "components": {"securitySchemes": {}},
        }
        if self.description:
            spec["info"]["description"] = self.description
        if self.servers:
            spec["servers"] = self.servers
        for url, endpoint in self.rules:
            self._add_operations(spec, url, endpoint)
        if not spec["components"]["securitySchemes"]:
            spec.pop("components")
        return spec

    def _add_operations(self, spec, url, endpoint):
        """Add one operation per HTTP method of the route."""
        routing = endpoint.routing
        api_doc = routing.get("api_doc") or {}
        if api_doc.get("exclude"):
            return
        path, path_params = openapi_path(url)
        ctx = DocContext(self.env, endpoint)
        input_schema = self._get_schema(routing, ctx, "input", url)
        output_schema = self._get_schema(routing, ctx, "output", url)
        content_type = api_doc.get("content_type") or "application/json"
        security = self._get_security(spec, routing.get("auth"))
        extra_params = self.ir_http._openapi_parameters(url, endpoint)
        summary, description = self._get_description(endpoint, api_doc)
        methods = routing.get("methods") or DEFAULT_METHODS
        for method in methods:
            if method in IGNORED_METHODS:
                continue
            op = {
                "operationId": api_doc.get("operation_id")
                or _slug(f"{method.lower()}_{path}"),
                "parameters": path_params + self.parameters + extra_params,
                "responses": dict(
                    {"200": schema_to_response(output_schema)}, **DEFAULT_RESPONSES
                ),
            }
            if summary:
                op["summary"] = summary
            if description:
                op["description"] = description
            if api_doc.get("tags"):
                op["tags"] = list(api_doc["tags"])
            if api_doc.get("deprecated"):
                op["deprecated"] = True
            if security is not None:
                op["security"] = security
            if input_schema:
                if method in QUERY_METHODS:
                    op["parameters"] = op["parameters"] + schema_to_query_parameters(
                        input_schema
                    )
                else:
                    op["requestBody"] = schema_to_request_body(
                        input_schema, content_type=content_type
                    )
            spec["paths"].setdefault(path, {})[method.lower()] = op

    def _get_schema(self, routing, ctx, direction, url):
        """Return the JSON schema for given direction, or None if not available.

        Params (`input`/`output` routing keys) win over plain `api_doc` schemas.
        Some schemas depend on the request: they must not break the whole document.
        """
        param = routing.get(direction)
        if not hasattr(param, "to_json_schema"):
            return (routing.get("api_doc") or {}).get(f"{direction}_schema")
        try:
            return param.to_json_schema(ctx, direction)
        except Exception as err:
            # Eg: schemas depending on the request.
            # Do not break the whole document for one route.
            _logger.warning(
                "Cannot get %s schema for %s: %s", direction, url, err, exc_info=True
            )
            return None

    def _get_security(self, spec, auth):
        """Register the security scheme of the auth method and reference it."""
        scheme = self.ir_http._openapi_security_scheme(auth)
        if not scheme:
            return None
        name, definition = scheme
        spec["components"]["securitySchemes"][name] = definition
        return [{name: []}]

    def _get_description(self, endpoint, api_doc):
        """Texts from `api_doc` or, as fallback, from the docstring of the endpoint."""
        summary = api_doc.get("summary")
        description = api_doc.get("description")
        if summary or description:
            return summary, description
        func = getattr(endpoint, "func", endpoint)
        doc = inspect.getdoc(func) if callable(func) else ""
        doc = doc or ""
        summary, __, description = doc.partition("\n")
        return summary.strip() or None, description.strip() or None
