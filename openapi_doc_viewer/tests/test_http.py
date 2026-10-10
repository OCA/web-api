# Copyright 2026 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from unittest import mock

from odoo import http
from odoo.tests.common import HttpCase, new_test_user, tagged

from odoo.addons.openapi_doc_base.sources import DocSource


def _doc(title):
    return lambda env: {"openapi": "3.0.3", "info": {"title": title}, "paths": {}}


EXTRA_SOURCES = [
    DocSource("test.a1", "A1", _doc("A1"), category="cat_a", app="app_1"),
    DocSource(
        "test.s1", "S1", _doc("S1"), category="cat_a", groups=("base.group_system",)
    ),
]


class OpenApiDocTestController(http.Controller):
    @http.route(
        "/openapi_doc_test/documented",
        type="http",
        auth="public",
        methods=["GET"],
        api_doc={"group": "test_openapi_doc", "summary": "Documented controller"},
    )
    def documented(self):
        return ""


@tagged("-at_install", "post_install")
class TestHttp(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.registry.clear_cache("routing")
        new_test_user(
            cls.env,
            login="doc_viewer",
            password="doc_viewer",
            groups="base.group_user,openapi_doc_base.group_openapi_doc_viewer",
        )
        ir_http_cls = type(cls.env["ir.http"])
        orig = ir_http_cls._openapi_doc_sources

        def _sources(self):
            return orig(self) + EXTRA_SOURCES

        patcher = mock.patch.object(ir_http_cls, "_openapi_doc_sources", _sources)
        patcher.start()
        cls.addClassCleanup(patcher.stop)

    def test_page(self):
        """The page lists the sources the user may see, filterable by category."""
        self.authenticate("doc_viewer", "doc_viewer")
        response = self.url_open("/openapi/docs")
        self.assertEqual(response.status_code, 200)
        # Documented controllers are collected automatically
        self.assertIn("/openapi/docs/routes.test_openapi_doc.json", response.text)
        self.assertIn("/openapi/docs/test.a1.json", response.text)
        self.assertNotIn("test.s1.json", response.text)
        self.assertIn("category=cat_a", response.text)
        response = self.url_open("/openapi/docs?category=cat_a")
        self.assertNotIn("routes.test_openapi_doc.json", response.text)

    def test_document(self):
        """A source's document is served only to users allowed to see it."""
        self.authenticate("doc_viewer", "doc_viewer")
        response = self.url_open("/openapi/docs/routes.test_openapi_doc.json")
        self.assertIn("/openapi_doc_test/documented", response.json()["paths"])
        response = self.url_open("/openapi/docs/test.s1.json")
        self.assertEqual(response.status_code, 404)
        self.authenticate("admin", "admin")
        response = self.url_open("/openapi/docs/test.s1.json")
        self.assertEqual(response.json()["info"]["title"], "S1")

    def test_menu(self):
        """The docs menu is restricted to the viewer group."""
        menu = self.env.ref("openapi_doc_viewer.menu_openapi_docs")
        self.assertEqual(
            menu.groups_id, self.env.ref("openapi_doc_base.group_openapi_doc_viewer")
        )
