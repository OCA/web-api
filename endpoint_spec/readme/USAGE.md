## Declare endpoints

    from odoo.addons.endpoint_spec.endpoint import collect_endpoints, endpoint

    class MyService:

        @endpoint("GET", path="/<int:id>")
        def get(self, id):
            ...

        @endpoint(input=MyParam(), output=MyParam())
        def scan(self, barcode):
            ...

    specs = collect_endpoints(MyService)
    # {"get": EndpointSpec(...), "scan": EndpointSpec(...)}

The decorator only declares metadata: it does not wrap the method.
Methods can call each other and tests can call them directly.

Specs are inherited: an override w/o decorator keeps the spec of its parent.
Use `@endpoint.extend(...)` on an override to change only some values.

Decorated methods w/o path get `/<method name>` as default path.
Non decorated methods are not exposed.

Use the specs in a routes generator: one route per path of each `EndpointRoute`,
w/ the HTTP methods, the `input` / `output` params and the `routing` keys of the spec.

## Conventions

By default only decorated methods are exposed: this is the recommended behavior.

To expose non decorated methods, pass your own `Conventions` subclass
to `collect_endpoints` and implement `guess`. Use it only as a transition,
eg: to migrate services from `base_rest` w/o declaring every endpoint at once
(see `ShopfloorConventions` in `shopfloor_base`). With implicit exposure,
any new public method becomes an endpoint by mistake.
