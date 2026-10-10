# Copyright 2026 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import functools
import logging

from odoo import models, tools

from ..builder import SpecBuilder
from ..sources import DocSource, filter_sources

_logger = logging.getLogger(__name__)

DEFAULT_GROUP = "default"
SECURITY_SCHEMES = {
    "user": ("odooSession", {"type": "apiKey", "in": "cookie", "name": "session_id"}),
    "api_key": ("apiKey", {"type": "apiKey", "in": "header", "name": "API-KEY"}),
}


class IrHttp(models.AbstractModel):
    """Registry of documentation sources and hooks for generated documents."""

    _inherit = "ir.http"

    # Sources

    def _openapi_doc_sources(self):
        """Return all the `DocSource` available.

        By default, one source per `api_doc` group of the routes having
        an `api_doc` routing key, whatever their type (category `routes`).
        Extend it to register your own sources.
        """
        groups = sorted({group for group, __, __ in self._openapi_routing_map_rules()})
        return [
            DocSource(
                key=f"routes.{group}",
                title=group,
                build=functools.partial(self._openapi_build_routes_doc, group),
                category="routes",
            )
            for group in groups
        ]

    def _openapi_doc_sources_for(self, category=None, app=None):
        """Return the sources matching given category and app."""
        return filter_sources(self._openapi_doc_sources(), category=category, app=app)

    def _openapi_doc_category_label(self, category):
        """Label of a category in the UI. Extend it to show a readable name."""
        return {"routes": "Routes"}.get(category, category)

    def _openapi_doc_source(self, key):
        """Return the source matching `key` or None."""
        for source in self._openapi_doc_sources():
            if source.key == key:
                return source
        return None

    @tools.ormcache("key", cache="routing")
    def _openapi_doc(self, key):
        """Return the OpenAPI document of the source (cached).

        The cache is cleared every time the routing map changes.
        """
        source = self._openapi_doc_source(key)
        if not source:
            return None
        return source.build(self.env)

    def _openapi_routing_map_rules(self):
        """Yield `(group, url, endpoint)` for routes w/ an `api_doc` routing key."""
        try:
            routing_map = self.routing_map()
        except RuntimeError as err:
            # Some overrides of `routing_map` need a request (eg: older versions
            # of `endpoint_route_handler`): do not break the other sources.
            _logger.warning("Routing map not available w/o request: %s", err)
            return
        for rule in routing_map.iter_rules():
            api_doc = rule.endpoint.routing.get("api_doc")
            if not api_doc:
                continue
            yield api_doc.get("group") or DEFAULT_GROUP, rule.rule, rule.endpoint

    def _openapi_build_routes_doc(self, group, env):
        """Build the document of the documented routes of a group."""
        rules = [
            (u, e) for grp, u, e in self._openapi_routing_map_rules() if grp == group
        ]
        return SpecBuilder(env, rules, title=group).build()

    # Builder hooks

    def _openapi_security_scheme(self, auth):
        """Return `(name, OpenAPI security scheme)` for given auth or None."""
        return SECURITY_SCHEMES.get(auth)

    def _openapi_parameters(self, url, endpoint):
        """Return extra OpenAPI parameters for the route (eg: headers)."""
        return []

    # Servers

    def _openapi_server_urls(self):
        """Return `[(label, url)]` of base URLs proposed to try requests.

        Used for "Try it out" and curl snippets. The URL of the current page
        is always proposed first (by the page itself) and used by default:
        `web.base.url` might be an internal URL.
        Extra URLs can be set (comma separated) in the system parameter
        `openapi_doc_base.server_urls`.
        """
        param = self.env["ir.config_parameter"].sudo()
        candidates = [("web.base.url", param.get_param("web.base.url") or "")]
        extra = param.get_param("openapi_doc_base.server_urls") or ""
        candidates += [(url.strip(), url.strip()) for url in extra.split(",")]
        res = []
        for label, url in candidates:
            url = url.rstrip("/")
            if url and url not in [u for __, u in res]:
                res.append((label, url))
        return res

    # Access

    def _openapi_doc_category_groups(self):
        """Return `{category: groups xmlids}` protecting whole categories.

        Applied on top of the groups of each source. Extend it to protect your category.
        """
        return {}

    def _openapi_doc_can_access(self, source):
        """Return True if the current user can see the source.

        The user must belong to the groups of the source
        and to the groups of its category, if any.
        """
        user = self.env.user
        category_groups = self._openapi_doc_category_groups().get(source.category)
        return all(
            user.has_groups(",".join(groups))
            for groups in (source.groups, category_groups)
            if groups
        )

    def _openapi_doc_sources_for_user(self, category=None, app=None):
        """Return the sources matching given category and app visible to the user."""
        return [
            s
            for s in self._openapi_doc_sources_for(category=category, app=app)
            if self._openapi_doc_can_access(s)
        ]
