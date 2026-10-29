Two independent parts:

- **collect** routes and describe them (no URL involved)
- **expose** documents via your own controller

## Document controllers: no inheritance needed

Add an `api_doc` routing key to the route, whatever its type.
Nothing else is needed: documented routes are collected automatically
from the routing map, one source per `api_doc` group (category `routes`).

    @http.route(
        "/my/api/partner/<int:id>",
        type="http",
        auth="user",
        methods=["GET"],
        api_doc={
            "group": "partners",
            "tags": ["partner"],
            "output_schema": {"type": "object", "properties": {"name": {"type": "string"}}},
        },
    )
    def get(self, id):
        """Get a partner.

        Return the main information of the partner.
        """

`api_doc` keys:

| Key | Meaning |
|---|---|
| `group` | source the route belongs to (default: `default`) |
| `summary`, `description` | texts of the operation (default: the docstring of the endpoint) |
| `tags` | OpenAPI tags |
| `operation_id` | OpenAPI operation id (default: generated from method and path) |
| `deprecated` | flag the operation as deprecated |
| `exclude` | do not document the route |
| `input_schema`, `output_schema` | JSON schemas of the request and the response |
| `content_type` | content type of the request body (default: `application/json`) |

Instead of plain schemas, routes can provide `input` and `output` routing keys
holding objects w/ a `to_json_schema(ctx, direction)` method (eg: `http_api_dispatcher` params).

GET and DELETE input schemas are documented as query parameters,
other methods get a request body.

This module exposes no URL: to show these documents,
serve the sources of category `routes` from a controller (see *Expose docs*).

## Document records: `openapi.doc.mixin`

When routes come from records (eg: configurable endpoints),
inherit `openapi.doc.mixin` and implement `_openapi_route_info`:

    class MyRoute(models.Model):
        _name = "my.route"
        _inherit = ["my.route", "openapi.doc.mixin"]

        def _openapi_route_info(self):
            return self.route, {"methods": [self.method], "auth": "user"}

The mixin adds the docs fields (opt-in flag, description, tags,
input/output JSON schemas), refreshes cached documents when they change
and provides `_openapi_rule()` and `_openapi_build_doc(title)`
to use the records w/ `SpecBuilder`. Add the fields to your views
and register a source (see below). See `endpoint_openapi` for a real use case.

## Register sources

Besides the `routes` sources, register your own by extending
`ir.http._openapi_doc_sources`:

    from odoo.addons.openapi_doc_base.builder import SpecBuilder
    from odoo.addons.openapi_doc_base.sources import DocSource

    class IrHttp(models.AbstractModel):
        _inherit = "ir.http"

        def _openapi_doc_sources(self):
            sources = super()._openapi_doc_sources()
            for app in self.env["my.app"].sudo().search([]):
                sources.append(
                    DocSource(
                        key=f"my_app.{app.id}",
                        title=app.name,
                        build=app._build_api_doc,
                        category="my_app",
                        app=app.name,
                        groups=("my_module.group_my_app_manager",),
                    )
                )
            return sources

`build` receives the env and returns the document,
for instance `SpecBuilder(env, rules, title=..., version=...).build()`
where `rules` is a list of `(url, endpoint)`. `endpoint` can be any object
with a `routing` dict. Documents are cached until the routing map changes.

## Expose docs

Define your own controller (URL, auth, access) and use `OpenApiDocsControllerMixin`,
a plain python helper for controllers (unrelated to the `openapi.doc.mixin` model):

    from odoo import http
    from odoo.addons.openapi_doc_base.http import OpenApiDocsControllerMixin

    class MyDocs(http.Controller, OpenApiDocsControllerMixin):

        def _sources(self):
            return http.request.env["ir.http"].sudo()._openapi_doc_sources_for("my_app")

        @http.route("/my/api-docs", type="http", auth="user")
        def index(self, category=None, app=None):
            return self._openapi_index_response(
                self._sources(),
                "/my/api-docs",
                lambda source: f"/my/api-docs/{source.key}.json",
                category=category,
                app=app,
            )

        @http.route("/my/api-docs/<string:key>.json", type="http", auth="user")
        def document(self, key):
            return self._openapi_document_response(self._sources(), key)

The page shows Swagger UI for the selected sources and links to select
a category or an app when there's more than one.

To show documented controllers, pass the sources of category `routes`:
`_openapi_doc_sources_for("routes")`.
Only the sources passed to the helpers are served.

## Try it out

The top bar of the page has a *Server* selector: the base URL used by
"Try it out" and by the curl snippets. By default it's the *current domain*
(the one of the page), not `web.base.url` (which might be an internal URL).
Other choices: `web.base.url` and the URLs listed in the system parameter
`openapi_doc_base.server_urls`. The choice is remembered by the browser.

## Access

Docs are protected by groups, always:

- each source has `groups` (any of them is required).
  Default: *API docs: viewer* (`openapi_doc_base.group_openapi_doc_viewer`),
  implied by *Settings*. Sources w/o groups are refused.
- whole categories can require more groups:
  extend `ir.http._openapi_doc_category_groups()` (`{category: groups}`)

`OpenApiDocsControllerMixin` serves only the sources visible to the current user
(404 otherwise). To serve docs to other audiences (eg: public docs for one app),
override `_openapi_accessible_sources` in your controller, deliberately.

## Customize

- `ir.http._openapi_security_scheme(auth)`: security scheme per auth method
  (`user` and `api_key` are supported out of the box)
- `ir.http._openapi_parameters(url, endpoint)`: extra parameters, eg: headers
- `ir.http._openapi_doc_can_access(source)`: access check per source
- `OpenApiDocsControllerMixin._openapi_accessible_sources(sources)`: policy of a controller
