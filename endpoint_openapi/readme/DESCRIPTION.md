Document configurable endpoints (`endpoint.endpoint` and any model using
`endpoint.mixin`, eg: `edi.endpoint`) with OpenAPI and browse them with Swagger UI.

Endpoints are documented only when enabled on the record:
they might be meant for internal use only.

Technically, it plugs `endpoint.mixin` into `openapi.doc.mixin` (from `openapi_doc_base`)
and registers one docs source per model and route group.
