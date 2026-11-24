On the webservice backend, set the authentication type to "Client Certificate" and fill in:

* **Client Certificate Path:** path to the certificate file (or to a single file containing both the certificate and the private key).
* **Client Private Key Path:** optional, leave empty if the private key is bundled in the certificate file.

To manage these paths with `server_environment`, see `webservice_client_certificate_auth_server_env`.
