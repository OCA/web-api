# Copyright 2026 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
"""Defaults for endpoint specs and collection of the endpoints of a class."""

from .spec import EndpointRoute, find_spec
from .utils import as_tuple, public_methods


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
        methods = as_tuple(methods) or ("POST",)
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
