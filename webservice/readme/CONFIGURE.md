## Upgrade from versions prior to 18.0.2.0.1

On upgrade from a version prior to `18.0.2.0.1`, a
`webservice.request_content_only` system parameter is created automatically
(see that version's migration script) to preserve the previous default
behavior of HTTP calls, which returned only the response content instead of
the full `requests.Response` object.

If your code relies on that implicit default, keep the parameter for now.
Once it's adapted to use the full response object (see *Usage*), delete the
parameter under *Settings > Technical > System Parameters* - new installs
never get it set.

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
