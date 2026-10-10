# Copyright 2026 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import dataclasses
from collections.abc import Callable

DEFAULT_GROUPS = ("openapi_doc_base.group_openapi_doc_viewer",)


@dataclasses.dataclass(frozen=True)
class DocSource:
    """One OpenAPI document.

    :param key: unique identifier, usable in URLs
    :param title: shown in the UI
    :param build: callable `(env) -> dict` returning the OpenAPI document
    :param category: group of sources (eg: `shopfloor`, `endpoint`)
    :param app: optional sub-group within the category (eg: an app, a backend)
    :param sequence: order in the UI
    :param groups: xmlids of the groups allowed to see the source (any of them).
        Mandatory: docs must never be visible by accident.
    """

    key: str
    title: str
    build: Callable
    category: str = "default"
    app: str = None
    sequence: int = 10
    groups: tuple = DEFAULT_GROUPS

    def __post_init__(self):
        """Refuse unprotected sources."""
        if not self.groups:
            raise ValueError(f"Doc source {self.key} must be protected by groups")


def filter_sources(sources, category=None, app=None):
    """Return sources matching given category and app, sorted for the UI."""
    res = [
        s
        for s in sources
        if (not category or s.category == category) and (not app or s.app == app)
    ]
    return sorted(res, key=lambda s: (s.category, s.app or "", s.sequence, s.title))
