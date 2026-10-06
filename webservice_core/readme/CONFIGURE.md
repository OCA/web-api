Go to *Settings > Technical > WebService Backend* (requires the
*Administration / Settings* group) and create a new backend:

- **Name** / **Technical Name**: a label and a unique technical key you'll
  use to look the backend up from code (e.g. `env.ref` is not used here;
  search by `tech_name` instead).
- **Protocol**: only `HTTP Request` is available in this module.
- **URL**: the base URL every call is relative to, e.g.
  `https://api.example.com`. It may contain `{placeholder}` tokens (see
  *Usage*), e.g. `https://api.example.com/{endpoint}`.
- **Content-Type**: optional default `Content-Type` header for every call.
- **Timeout**: optional timeout in seconds for the whole request (connect +
  read). Left empty, a call waits indefinitely.

Under the **Headers** and **Querystring Params** tabs you can configure
static defaults, merged into every call (see *Usage*).

Then configure authentication via **Auth Type**:

- **Public**: no credentials needed.
- **Username & password**: sent as HTTP Basic Auth. Requires **Username**
  and **Password**.
- **API Key**: sent as a custom header. Requires **API Key** and
  **API Key header** (the header name to send it under, e.g. `X-Api-Key`).

Required fields depend on the selected auth type; the form only shows and
requires the ones that apply, and saving enforces it.

Each `webservice.endpoint` (see *Description*) has its own Content-Type,
Timeout, Headers and Querystring Params, overriding the backend's own for
that specific endpoint - set only what needs to differ.
