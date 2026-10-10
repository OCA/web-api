Declare endpoints on any class (eg: services), not only on controllers.

Provides the metadata that routes generators (see `endpoint_route_handler`)
read to build routes: HTTP methods, paths, input/output params and any routing key.

- `endpoint` decorator: declares metadata only, it never wraps the method
- `EndpointSpec`: the metadata of an endpoint
- `collect_endpoints`: collect the specs of a class, following inheritance
- conventions: defaults for non decorated methods

It does not depend on any dispatcher: generated routes can use
any route type (eg: `http_json`, `restapi` from `base_rest`).
