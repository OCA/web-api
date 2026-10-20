On the endpoint form, open the *API docs* tab:

- enable *Show in API docs*
- optionally add a description, tags, and the JSON schemas of the input
  (params or body) and of the output (response)

Then open *Settings > Technical > API docs* (`/openapi/docs`, from `openapi_doc_viewer`):

- one document per model (category) and route group (app)
- use the links at the top to filter by model and route group
- docs are visible to the *API docs: viewer* group. To restrict endpoint docs further,
  extend `ir.http._openapi_doc_category_groups` for the model (category)

Each document is also available as JSON at
`/openapi/docs/<model>.<route group>.json`.

The request content type of the endpoint is used for the request body,
the auth type for the security scheme.
