On upgrade from a version prior to `18.0.2.0.1`, a
`webservice.request_content_only` system parameter is created automatically
(see that version's migration script) to preserve the previous default
behavior of HTTP calls, which returned only the response content instead of
the full `requests.Response` object.

If your code relies on that implicit default, keep the parameter for now.
Once it's adapted to use the full response object (see *Usage*), delete the
parameter under *Settings > Technical > System Parameters* - new installs
never get it set.
