# Copyright 2026 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
"""Declare endpoints on classes that are not controllers.

Controllers declare their routes w/ `odoo.http.route`.
This module is for service-like classes whose methods are turned into
routes by a generator (see `endpoint_route_handler` generators):

    class MyService:

        @endpoint("GET", path="/<int:id>")
        def get(self, id):
            ...

        @endpoint(input=MyParam(), output=MyParam())
        def scan(self, barcode):
            ...

    specs = collect_endpoints(MyService)

The decorator only declares metadata: it never wraps the method.
Validation happens in the dispatcher, at the HTTP boundary.
Hence, methods can call each other and tests can call them directly.
"""

from .spec import ENDPOINT_ATTR, ENDPOINT_EXTEND_ATTR, EndpointRoute, EndpointSpec
from .utils import as_tuple


def endpoint(methods="POST", path=None, input=None, output=None, **routing):
    """Declare a method as endpoint.

    :param methods: HTTP method(s)
    :param path: path(s) relative to the root of the generator.
        If not given, conventions provide the default path.
    :param input: param object for request params
    :param output: param object for the result
    :param routing: any other routing key (auth, cors, csrf, api_doc, ...)
    """
    methods = as_tuple(methods)
    routes = ()
    if path:
        routes = (EndpointRoute(paths=as_tuple(path), methods=methods),)
    spec = EndpointSpec(
        routes=routes, methods=methods, input=input, output=output, routing=routing
    )

    def deco(func):
        """Store the spec on the function, untouched."""
        setattr(func, ENDPOINT_ATTR, spec)
        return func

    return deco


def extend(**values):
    """Update the spec inherited from parent classes.

    Use it on overrides to change only some values:

        @endpoint.extend(routing={"api_doc": {"tags": ["new"]}})
        def scan(self, barcode):
            return super().scan(barcode)
    """

    def deco(func):
        """Store the values to merge into the inherited spec."""
        setattr(func, ENDPOINT_EXTEND_ATTR, values)
        return func

    return deco


endpoint.extend = extend
