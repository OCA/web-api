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

import dataclasses
import inspect
from collections.abc import Mapping
from typing import Any

ENDPOINT_ATTR = "_endpoint_spec"
ENDPOINT_EXTEND_ATTR = "_endpoint_spec_extend"


@dataclasses.dataclass(frozen=True)
class EndpointRoute:
    """Paths served with the same HTTP methods."""

    paths: tuple
    methods: tuple


@dataclasses.dataclass(frozen=True)
class EndpointSpec:
    """Metadata of an endpoint.

    :param routes: tuple of `EndpointRoute`.
        Paths are relative to the root of the generator.
        When no route is given, conventions provide the default one.
    :param methods: HTTP methods to use for the default route
    :param input: param object for request params (eg: an `http_json_dispatcher` param)
    :param output: param object for the result
    :param routing: any other routing key (auth, cors, csrf, api_doc, ...)
    """

    routes: tuple = ()
    methods: tuple = ()
    input: Any = None
    output: Any = None
    routing: Mapping = dataclasses.field(default_factory=dict)

    def merge(self, **values):
        """Return a new spec updated with given values.

        `routing` values are merged, other values are replaced.
        """
        if "routing" in values:
            values["routing"] = dict(self.routing, **values["routing"])
        return dataclasses.replace(self, **values)


def _as_tuple(value):
    """Normalize a single value or an iterable to a tuple."""
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(value)


def endpoint(methods="POST", path=None, input=None, output=None, **routing):
    """Declare a method as endpoint.

    :param methods: HTTP method(s)
    :param path: path(s) relative to the root of the generator.
        If not given, conventions provide the default path.
    :param input: param object for request params
    :param output: param object for the result
    :param routing: any other routing key (auth, cors, csrf, api_doc, ...)
    """
    methods = _as_tuple(methods)
    routes = ()
    if path:
        routes = (EndpointRoute(paths=_as_tuple(path), methods=methods),)
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


def find_spec(cls, name):
    """Return the spec of method `name` looking up the class hierarchy.

    An override without decorator keeps the spec of its parent.
    `endpoint.extend` updates on overrides are applied
    from the parent to the child.
    """
    extensions = []
    for klass in cls.__mro__:
        func = klass.__dict__.get(name)
        if func is None:
            continue
        func = getattr(func, "__func__", func)
        ext = getattr(func, ENDPOINT_EXTEND_ATTR, None)
        if ext:
            extensions.append(ext)
        spec = getattr(func, ENDPOINT_ATTR, None)
        if spec is not None:
            for ext in reversed(extensions):
                spec = spec.merge(**ext)
            return spec
    return None


def public_methods(cls):
    """Return `(name, func)` of public methods without triggering properties."""
    res = []
    for attr in inspect.classify_class_attrs(cls):
        if attr.kind != "method" or attr.name.startswith("_"):
            continue
        res.append((attr.name, getattr(cls, attr.name)))
    return sorted(res)


class Conventions:
    """Provide defaults for endpoint specs.

    The base class exposes only decorated methods
    and uses `/<method name>` as default path.
    This is the recommended behavior: endpoints are declared explicitly.

    Subclasses can expose non decorated methods via `guess`.
    This is meant only as a transition, eg: to migrate services from `base_rest`
    (see `ShopfloorConventions` in `shopfloor_base`).
    """

    def guess(self, cls, name, func):
        """Return a spec for a non decorated method or None to skip it."""
        return None

    def default_routes(self, cls, name, func, methods=None):
        """Default route: POST (or given methods) on `/<method name>`."""
        methods = _as_tuple(methods) or ("POST",)
        return (EndpointRoute(paths=(f"/{name}",), methods=methods),)

    def complete(self, cls, name, func, spec):
        """Fill the missing values of a spec."""
        if not spec.routes:
            routes = self.default_routes(cls, name, func, spec.methods or None)
            spec = spec.merge(routes=routes)
        return spec


def collect_endpoints(cls, conventions=None):
    """Return `{method name: EndpointSpec}` for the endpoints of `cls`.

    Decorated methods (on the class or its parents) are always collected.
    Non decorated public methods are passed to `conventions.guess`.
    """
    conventions = conventions or Conventions()
    res = {}
    for name, func in public_methods(cls):
        spec = find_spec(cls, name)
        if spec is None:
            spec = conventions.guess(cls, name, func)
        if spec is None:
            continue
        res[name] = conventions.complete(cls, name, func, spec)
    return res
