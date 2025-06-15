This module is meant to be used from server-side code.

Basic usage
===========

1. Create a `webservice.backend` record (see *Configuration*).
2. From Python code, fetch the backend and call HTTP methods.

Example: simple GET
-------------------

```python
backend = self.env["webservice.backend"].get_by_tech_name("demo_ws")
result = backend.call("get", url="api/v1/ping")
```

- If `url` is relative, it is joined with the backend `url`.
- If `url` is an absolute URL, it is used as-is.

Example: POST JSON payload
-------------------------

```python
import json

backend = self.env["webservice.backend"].get_by_tech_name("demo_ws")
payload = {"name": "John"}

result = backend.call(
    "post",
    url="api/v1/contacts",
    data=json.dumps(payload),
    headers={"Accept": "application/json"},
    content_type="application/json",
)
```

Getting the full `requests.Response`
-----------------------------------

By default, calls return `response.content`.
To get the full `requests.Response`, set `content_only` to `False`:

```python
backend = self.env["webservice.backend"].get_by_tech_name("demo_ws")
response = backend.call("get", url="api/v1/ping", content_only=False)
status_code = response.status_code
body = response.content
```

Timeouts
--------

You can override timeouts per call using `timeout` (as accepted by `requests`):

- A single number applies to both the connect and read timeouts.
- A tuple `(connect_timeout, read_timeout)` allows setting them separately.

```python
backend = self.env["webservice.backend"].get_by_tech_name("demo_ws")
result = backend.call("get", url="api/v1/ping", timeout=(2, 10))
```

URL formatting with parameters
------------------------------

If your backend URL or endpoint contains format placeholders, pass `url_params`:

```python
backend = self.env["webservice.backend"].get_by_tech_name("demo_ws")
backend.url = "https://api.example.com/{version}/"
result = backend.call("get", url="resources/{resource_id}", url_params={"version": "v1", "resource_id": 42})
```
