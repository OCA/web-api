# Copyright 2026 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
"""Endpoint metadata and its lookup along the class hierarchy."""

import dataclasses
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
    :param input: param object for request params (eg: an `http_api_dispatcher` param)
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
