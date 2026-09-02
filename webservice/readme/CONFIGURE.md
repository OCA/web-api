## OAuth2 (Client Credentials)

For the *Backend Application (Client Credentials Grant)* flow, two extra options
control how the token is requested, so that endpoints which deviate from the
OAuth2 spec can still be used:

- **Token Request Method**: `POST` (default) or `GET`. Most providers expose the
  token endpoint as a POST; some require a GET.
- **Client Authentication**: how the client credentials are presented to the
  token endpoint:
  - *Client ID & Secret (HTTP Basic)* (default): the client id and secret are
    sent as an `Authorization: Basic base64(client_id:client_secret)` header
    (`client_secret_basic`).
  - *Custom Authorization header*: a static header value is sent verbatim. The
    **Client Auth Header** (default `Authorization`) and **Client Auth Header
    Value** are configured directly; the Client ID / Client Secret fields are
    not used in this case.

### Example: custom Authorization header

Some providers require the credentials in a non-standard Authorization header
(for instance Okta uses `Authorization: SSWS <token>`). Such an endpoint can be
configured as:

    Auth Type             = OAuth2
    OAuth2 Flow           = Backend Application (Client Credentials Grant)
    Token URL             = https://provider.example.com/oauth2/token
    Token Request Method  = GET
    Client Authentication = Custom Authorization header
    Client Auth Header    = Authorization
    Client Auth Value     = SSWS <token>

When a database is neutralized, stored webservice backend credentials
(username, password, API key, OAuth2 client id/secret/token, custom
OAuth2 auth header value) are cleared.
