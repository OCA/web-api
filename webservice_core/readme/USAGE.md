Look up the backend (e.g. by its technical name) and call it:

```python
backend = env["webservice.backend"].search([("tech_name", "=", "my_api")])
result = backend.call("get")  # -> requests.Response
result.content
result.status_code
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
merged on top of the backend's own `Content-Type` and auth-derived headers
(e.g. the API key header):

```python
backend.call("get", headers={"X-Request-Id": "42"})
```

**Auth override**: pass `auth` to bypass the backend's configured auth type
for a single call (same format `requests` itself accepts, e.g. a
`(user, password)` tuple):

```python
backend.call("get", auth=("other_user", "other_password"))
```

