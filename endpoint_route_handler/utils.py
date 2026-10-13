# Copyright 2026 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
"""Helpers to build endpoints for the routing map."""

import functools
import importlib

from odoo import http

from .exceptions import EndpointHandlerNotFound

# Routing keys read by Odoo without a default value
# (see `odoo.http.Request._serve_db` and `ir.http._authenticate`).
# Endpoints generated outside of the standard controller machinery
# must provide them.
ROUTING_DEFAULTS = {
    "type": "http",
    "auth": "user",
    "methods": None,
    "readonly": False,
}


def make_endpoint(func, routing, pargs=(), kwargs=None):
    """Build an endpoint ready to be loaded in the routing map.

    :param func: callable handling the request
    :param routing: routing information (must contain ``routes``),
        missing mandatory keys are filled with ``ROUTING_DEFAULTS``
    :param pargs: positional arguments bound to ``func``
    :param kwargs: keyword arguments bound to ``func``
    :return: a ``functools.partial`` carrying the ``routing`` attribute
    """
    endpoint = functools.partial(func, *pargs, **(kwargs or {}))
    functools.update_wrapper(endpoint, func)
    routing = dict(ROUTING_DEFAULTS, **routing)
    if not routing.get("routes"):
        raise ValueError(f"No route defined for {func}")
    if routing["type"] not in http._dispatchers:
        raise ValueError(f"Unknown routing type `{routing['type']}` for {func}")
    endpoint.routing = routing
    return endpoint


def import_method(klass_dotted_path, method_name):
    """Import the class from its dotted path and return the bound method."""
    mod_path, klass_name = klass_dotted_path.rsplit(".", 1)
    try:
        mod = importlib.import_module(mod_path)
    except ImportError as exc:
        raise EndpointHandlerNotFound(f"Module `{mod_path}` not found") from exc
    try:
        klass = getattr(mod, klass_name)
    except AttributeError as exc:
        raise EndpointHandlerNotFound(f"Class `{klass_name}` not found") from exc
    try:
        return getattr(klass(), method_name)
    except AttributeError as exc:
        raise EndpointHandlerNotFound(f"Method name `{method_name}` not found") from exc


class RouteConflictTracker:
    """Track the routes of the routing map to detect conflicting ones.

    Without this check, a route declared twice is silently shadowed:
    werkzeug matches the first rule only.

    Matching rules:

    * URL: exact match of the URL as declared (routes are indexed by URL,
      one dict lookup). URLs that differ only by their placeholders
      (eg: `/foo/<int:id>` vs `/foo/<string:name>`) are not detected.
    * methods: the sets of methods intersect, eg: `{GET, POST}` vs `{POST}`.
      No methods means any method: it overlaps w/ everything.
      Same URL w/ different methods is fine, eg: GET and POST on `/foo`.

    A plain hash of `(url, methods)` would only catch identical method sets.
    """

    def __init__(self):
        # URL -> list of `(methods, owner)`
        self._routes = {}

    @staticmethod
    def methods(endpoint):
        """Methods of an endpoint as a set, None for any method."""
        methods = endpoint.routing.get("methods")
        return set(methods) if methods else None

    @classmethod
    def methods_label(cls, endpoint):
        """Methods of an endpoint for logs."""
        methods = cls.methods(endpoint)
        return ",".join(sorted(methods)) if methods else "(any method)"

    @staticmethod
    def controller_owner(endpoint):
        """Human readable owner of a standard controller route, for logs."""
        func = getattr(endpoint, "func", endpoint)
        return f"controller {func.__module__}.{func.__qualname__}"

    @staticmethod
    def rule_owner(endpoint_rule):
        """Human readable owner of a custom endpoint rule route, for logs."""
        return f"endpoint rule {endpoint_rule.key}"

    def add(self, url, endpoint, owner):
        """Remember the methods served on `url` and by whom."""
        self._routes.setdefault(url, []).append((self.methods(endpoint), owner))

    def conflict(self, url, endpoint):
        """Return the owner of a route already serving `url` w/ overlapping methods."""
        methods = self.methods(endpoint)
        for other_methods, owner in self._routes.get(url, ()):
            if methods is None or other_methods is None or methods & other_methods:
                return owner
        return None
