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
Flag a header or a querystring param as **Secret** when its value is a
token, a key, ...: the value is hidden in the UI and dropped when the
database is neutralized.

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

**Access rights**

- Configuring the webservice records (backends, endpoints, headers,
  querystring params) requires the *Administration / Settings* group.
- Calling them requires the *Webservice User* group, which gives read
  access to the webservice records. The `call*` methods are not available
  via RPC: they can only be called from server-side code, which should
  decide who may trigger a call.
- The credentials (API key, password, OAuth2 secrets and token, header and
  querystring param values) can be read by administrators only. A call
  reads the configuration as superuser, after checking that the current user
  can read the endpoint and its backend, and drops the data read from the
  cache at the end of the call.
