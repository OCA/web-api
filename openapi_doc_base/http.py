# Copyright 2026 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
"""Helpers for controllers exposing OpenAPI docs.

This module defines no route: each module exposes its own URLs
(and auth, access policy) and uses `OpenApiDocsControllerMixin` to serve the pages:

    class MyDocs(http.Controller, OpenApiDocsControllerMixin):

        @http.route("/my/api-docs", auth="user")
        def index(self, category=None, app=None):
            return self._openapi_index_response(
                self._my_sources(), "/my/api-docs", self._my_json_url,
                category=category, app=app,
            )

        @http.route("/my/api-docs/<string:key>.json", auth="user")
        def document(self, key):
            return self._openapi_document_response(self._my_sources(), key)
"""

import json
from urllib.parse import urlencode

from odoo.http import request

from .sources import filter_sources


class OpenApiDocsControllerMixin:
    """Serve Swagger UI and OpenAPI documents for a set of sources.

    Plain mixin (not a controller): it adds no route.
    """

    _openapi_template = "openapi_doc_base.swagger_ui"

    def _openapi_accessible_sources(self, sources):
        """Return the sources the current user can see (by groups).

        Override it only for a deliberate policy (eg: public docs for one app).
        """
        ir_http = request.env["ir.http"]
        return [s for s in sources if ir_http._openapi_doc_can_access(s)]

    def _openapi_index_response(
        self, sources, page_url, json_url, category=None, app=None, title="API docs"
    ):
        """Render Swagger UI for `sources`, w/ category and app selectors.

        :param sources: all the sources this page can show
        :param page_url: URL of the page itself (used by the selectors)
        :param json_url: callable `(source) -> URL` of its JSON document
        :param category: show only sources of this category
        :param app: show only sources of this app

        Only sources visible to the user are shown, 404 if none.
        """
        sources = self._openapi_accessible_sources(sources)
        if not sources:
            raise request.not_found()
        selected = filter_sources(sources, category=category, app=app)
        values = {
            "title": title,
            "categories": self._openapi_selector(
                page_url,
                sorted({s.category for s in sources}),
                category,
                "category",
                label=request.env["ir.http"]._openapi_doc_category_label,
            ),
            "apps": self._openapi_selector(
                page_url,
                sorted({s.app for s in filter_sources(sources, category) if s.app}),
                app,
                "app",
                extra={"category": category} if category else None,
            ),
            "servers": request.env["ir.http"].sudo()._openapi_server_urls(),
            "swagger_settings": json.dumps(
                {"urls": [{"name": s.title, "url": json_url(s)} for s in selected]}
            ),
        }
        return request.render(self._openapi_template, values)

    def _openapi_document_response(self, sources, key):
        """Return the JSON document of the source `key` among `sources`.

        404 if the source is unknown or not visible to the user.
        """
        sources = self._openapi_accessible_sources(sources)
        if key not in {s.key for s in sources}:
            raise request.not_found()
        doc = request.env["ir.http"].sudo()._openapi_doc(key)
        if doc is None:
            raise request.not_found()
        return request.make_json_response(doc)

    def _openapi_selector(
        self, page_url, values, current, param, extra=None, label=None
    ):
        """Return `[(label, url, active)]` links to filter the page.

        The 1st link (`All`) resets the filter.
        """
        if len(values) < 2:
            return []
        extra = extra or {}
        label = label or (lambda value: value)
        links = [("All", self._openapi_url(page_url, extra), not current)]
        for value in values:
            url = self._openapi_url(page_url, dict(extra, **{param: value}))
            links.append((label(value), url, value == current))
        return links

    def _openapi_url(self, page_url, params):
        """Build an URL w/ query params."""
        return f"{page_url}?{urlencode(params)}" if params else page_url
