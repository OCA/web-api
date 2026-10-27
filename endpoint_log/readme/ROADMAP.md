- Requests rejected before the endpoint is reached, such as an authentication failure
  or a request method the route does not accept, are not logged.
- The body of a form-encoded request is not logged, because Odoo parses it into the
  request parameters before the endpoint is reached.
- Logs are never deleted automatically.
