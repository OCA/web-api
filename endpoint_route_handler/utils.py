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
