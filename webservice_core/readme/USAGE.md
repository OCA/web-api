Look up the backend (e.g. by its technical name) and call it:

```python
backend = env["webservice.backend"].search([("tech_name", "=", "my_api")])
result = backend.call("get")  # -> the full requests.Response object
```

`call(method, *args, **kwargs)` accepts any of the standard HTTP verbs
(`get`, `post`, `put`, `delete`) and forwards everything else to
[requests](https://requests.readthedocs.io/), so any of its keyword
arguments work too (`data`, `json`, `params`, `files`, ...):

```python
backend.call("post", data=b"<xml>...</xml>")
backend.call("post", json={"foo": "bar"})
```

**URL**: by default the backend's own `url` is used. Pass `url` to hit a
different path - relative paths are appended to the backend's URL, a full
`http(s)://` URL is used as-is:

```python
backend.call("get", url="orders")  # -> <backend url>/orders
backend.call("get", url="https://other.example.com/orders")
```

If the backend's URL (or the `url` passed above) contains `{placeholder}`
tokens, fill them with `url_params`:

```python
# backend.url == "https://api.example.com/{endpoint}"
backend.call("get", url_params={"endpoint": "orders"})
```

**Headers**: pass `headers` to add/override headers for that call; they are
merged on top of the backend's own static headers (configured in the
"Headers" tab), `Content-Type` and auth-derived headers (e.g. the API key
header) - the `headers` kwarg wins on matching keys:

```python
backend.call("get", headers={"X-Request-Id": "42"})
```

**Querystring params**: sent via `requests`' `params=`, not to be confused
with `url_params` above, which fills `{placeholder}` tokens in the URL path
itself. Configure static defaults in the "Querystring Params" tab - a
value there may itself contain a `{placeholder}`, resolved against the
same `url_params` used for the URL. An explicit `params` kwarg passed to
`call()` wins over the static configuration on matching keys:

```python
backend.call("get", params={"verbose": "1"})
```

**Auth override**: pass `auth` to bypass the backend's configured auth type
for a single call (same format `requests` itself accepts, e.g. a
`(user, password)` tuple):

```python
backend.call("get", auth=("other_user", "other_password"))
```

**Timeout**: pass `timeout` to override the backend's own configured
timeout (in seconds) for a single call:

```python
backend.call("get", timeout=5)
```

**Response**: `call()` always returns the full `requests.Response` object
(status code, headers, content, ...):

```python
response = backend.call("get")
response.status_code
response.content
```
