Certificate paths are configured via `server_environment`.
Add the configuration section matching your backend's `tech_name` to your server environment files:

```
[webservice_backend.webservice_client_certificate_auth]
auth_type = client_certificate
client_certificate_path = /path/to/client.cert
# Optional: Leave empty if the private key is bundled in the certificate file
client_private_key_path = /path/to/client.key
```
