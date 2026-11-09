Base module to document HTTP endpoints with [OpenAPI](https://spec.openapis.org/oas/v3.0.3)
and browse the documents with Swagger UI.

It provides the building blocks, not the pages:

- `SpecBuilder`: build an OpenAPI document from any list of routes
  (from the routing map, from a routes generator, from records)
- documentation *sources*, grouped by category and app,
  registered via `ir.http._openapi_doc_sources`.
  Controllers w/ an `api_doc` routing key are collected automatically
- `openapi.doc.mixin`: docs fields and helpers for records that are routes
- `OpenApiDocsControllerMixin`: helpers for controllers to serve Swagger UI
  (with category and app selectors) and JSON documents

No URL is exposed by this module: each module exposing docs
defines its own routes, auth and access policy.

It does not depend on any API framework: any route can be documented
(see `endpoint_openapi` to document `endpoint` records,
or `http_api_dispatcher` params which describe their schemas).
