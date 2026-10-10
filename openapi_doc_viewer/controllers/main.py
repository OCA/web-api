# Copyright 2026 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import http
from odoo.http import request

from odoo.addons.openapi_doc_base.http import OpenApiDocsControllerMixin

DOCS_ROUTE = "/openapi/docs"


class OpenApiDocsController(http.Controller, OpenApiDocsControllerMixin):
    """One page for all the docs sources the user can see."""

    def _openapi_all_sources(self):
        """All the registered sources: the mixin keeps only the visible ones."""
        return request.env["ir.http"].sudo()._openapi_doc_sources_for()

    @http.route(DOCS_ROUTE, type="http", auth="user", methods=["GET"])
    def openapi_docs(self, category=None, app=None):
        """Swagger UI w/ category and app selectors."""
        return self._openapi_index_response(
            self._openapi_all_sources(),
            DOCS_ROUTE,
            lambda source: f"{DOCS_ROUTE}/{source.key}.json",
            category=category,
            app=app,
        )

    @http.route(
        f"{DOCS_ROUTE}/<string:key>.json", type="http", auth="user", methods=["GET"]
    )
    def openapi_doc(self, key):
        """OpenAPI document of one source."""
        return self._openapi_document_response(self._openapi_all_sources(), key)
