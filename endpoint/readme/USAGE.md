## Accessing request parameters

Code snippets receive the current HTTP request as the ``request``
variable. There are two ways to read the parameters sent by the client:

- ``request.params``: a flat ``dict`` populated by Odoo's dispatcher.
  For ``http`` routes it merges the query string, form-encoded body
  fields, uploaded files and path arguments; for ``json`` routes it
  contains the parsed JSON body and path arguments. Convenient for
  simple cases:

  ```python
  name = request.params.get("your_name", "")
  ```

  Since it is a plain ``dict``, repeated keys (e.g.
  ``?tag=a&tag=b``) collapse into a single value.

- ``request.httprequest.args``: a Werkzeug ``MultiDict`` containing
  **only** the query string parameters, regardless of the route type.
  Use it when you need to tell query string values apart from body
  fields, or when the same key is sent multiple times:

  ```python
  # GET /my/endpoint?tag=red&tag=blue&page=2
  tags = request.httprequest.args.getlist("tag")  # ["red", "blue"]
  page = request.httprequest.args.get("page")     # "2"
  ```

  ``getlist()`` is the only way to retrieve all the values of a
  repeated query string key.

For form-encoded ``POST``/``PUT`` bodies,
``request.httprequest.form`` provides the same ``MultiDict`` interface
for body fields. A JSON body sent to an ``http`` route is not exposed
through ``request.params``; read it with ``request.get_json_data()``
instead.
