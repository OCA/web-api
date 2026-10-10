Give the *API docs: viewer* group to the users that need to read the docs
(admins have it by default). Sources or categories protected by other groups
are shown only to their members.

Open `/openapi/docs` and use the links at the top to filter by category and app.
Each document is also available as JSON at `/openapi/docs/<source key>.json`.

You don't need this module to expose docs at your own URL
(eg: public docs for an app): define your own controller
w/ `OpenApiDocsControllerMixin` from `openapi_doc_base`.
