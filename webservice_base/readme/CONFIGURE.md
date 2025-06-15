To configure `webservice_base`:

1. Enable developer mode.
2. Go to *Settings > Technical > WebService Backend*.
3. Create a backend record:

   - **Protocol**: select `HTTP Request`
   - **URL**: base URL of the remote service, for example `https://api.example.com/`
   - **Content Type**: set a default `Content-Type` header (optional)
   - **Authentication**:

     - **Public**: no authentication
     - **Username & password**: set `Username` and `Password`
     - **API Key**: set `API Key header` (for example `Authorization` or `X-Api-Key`) and `API Key`

4. (Optional) Tune timeouts:

   - `Connect timeout`: seconds to establish the TCP connection
   - `Read timeout`: seconds to wait for the response

The backend record can be used directly from server-side code using the `call()` helper or the inherited adapter methods (`get`, `post`, `put`).
