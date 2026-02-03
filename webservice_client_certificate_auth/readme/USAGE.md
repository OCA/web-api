When a call is made using the backend, the adapter automatically injects the `cert` parameter into the underlying Python `requests`
call based on the provided configuration:

* **Certificate only:** Passed as `cert='/path/to/file'` (a single file containing the private key and the certificate).
* **Certificate and Key:** Passed as a tuple `cert=('/path/to/crt', '/path/to/key')`.

Warning: the private key to your local certificate must be unencrypted. Currently, `requests` does not support using encrypted keys.

See [Requests: Client Side Certificates](https://requests.readthedocs.io/en/latest/user/advanced/#client-side-certificates) for underlying implementation details.
