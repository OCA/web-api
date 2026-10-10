Viewer for OpenAPI docs: one page to browse all the docs the current user can see:
`/openapi/docs` (also in *Settings > Technical > API docs*).

The page lists the sources registered via `openapi_doc_base`
(documented controllers, configurable endpoints, apps...)
with links to filter them by category and app.

Each source is shown only to the users in its groups
(and in the groups of its category): see `openapi_doc_base`.
