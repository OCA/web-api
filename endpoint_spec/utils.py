# Copyright 2026 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
"""Helpers shared by the endpoint spec modules."""

import inspect


def as_tuple(value):
    """Normalize a single value or an iterable to a tuple."""
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(value)


def public_methods(cls):
    """Return `(name, func)` of public methods without triggering properties."""
    res = []
    for attr in inspect.classify_class_attrs(cls):
        if attr.kind != "method" or attr.name.startswith("_"):
            continue
        res.append((attr.name, getattr(cls, attr.name)))
    return sorted(res)
