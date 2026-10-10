## As a mixin

Use standard Odoo inheritance:

    class MyModel(models.Model):
        _name = "my.model"
        _inherit = "endpoint.route.handler"

Once you have this, each my.model record will generate a route. You can
have a look at the endpoint module to see a real life example.

The options of the routing rules are defined by the method
\_default_endpoint_options. Here's an example from the endpoint module:

    def _default_endpoint_options_handler(self):
        return {
            "klass_dotted_path": "odoo.addons.endpoint.controllers.main.EndpointController",
            "method_name": "auto_endpoint",
            "default_pargs": (self.route,),
        }

As you can see, you have to pass the references to the controller class
and the method to use when the endpoint is called. And you can prepare
some default arguments to pass. In this case, the route of the current
record.

## As a tool

Initialize non stored route handlers and generate routes from them. For
instance:

    route_handler = self.env["endpoint.route.handler.tool"]
    endpoint_handler = MyController()._my_handler
    vals = {
        "name": "My custom route",
        "route": "/my/custom/route",
        "request_method": "GET",
        "auth_type": "public",
    }
    new_route = route_handler.new(vals)
    new_route._register_controller()

You can override options and define - for instance - a different
controller method:

    options = {
        "handler": {
            "klass_dotted_path": "odoo.addons.my_module.controllers.SpecialController",
            "method_name": "my_special_handler",
        }
    }
    new_route._register_controller(options=options)

Of course, what happens when the endpoint gets called depends on the
logic defined on the controller method.

In both cases (mixin and tool) when a new route is generated or an
existing one is updated, the ir.http.routing_map (which holds all Odoo
controllers) will be updated.

You can see a real life example on shopfloor.app model.

## Generated routes

A rule can provide a `generator` instead of a `handler`.
The generator is called when the routing map is built
and yields any number of `(url, endpoint)` pairs.
This way, a single row in the `endpoint_route` table
can serve many routes computed from the code
(e.g. all the methods exposed by a set of services)
and new routes do not require any update of the table.

The preferred way is to point to a model method,
which can be extended via standard inheritance:

    def _prepare_endpoint_rules(self, options=None):
        options = {
            "generator": {
                "model": self._name,
                "res_id": self.id,
                "method_name": "_generate_routes",
            }
        }
        return super()._prepare_endpoint_rules(options=options)

    def _generate_routes(self, rule):
        for name in ("foo", "bar"):
            route = f"{rule.route}/{name}"
            endpoint = make_endpoint(
                MyController()._handle,
                {"routes": [route], "methods": ["POST"], "auth": "user"},
                pargs=(self.id, name),
            )
            yield route, endpoint

The method is called with superuser rights
as the routing map can be built by any user.
A python class can be used too, via `klass_dotted_path`,
like for handlers.

Use `utils.make_endpoint` to build endpoints:
it fills the routing keys that Odoo requires.

A generator must be fast, deterministic and must not write to the database.
If it fails, the error is logged and its routes are skipped:
the rest of the routing map is not affected.

The routes of the rule are refreshed when the rule changes
(the routing map version is bumped)
or when the code changes (as for any controller: restart the server).
