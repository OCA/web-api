# Copyright 2026 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from unittest import mock

from odoo import http
from odoo.tests.common import HttpCase, new_test_user, tagged

from ..http import OpenApiDocsControllerMixin
from ..sources import DocSource

ROUTE = "/openapi_doc_base_test"
GROUP = "test_openapi"


def _doc(title):
    return lambda env: {"openapi": "3.0.3", "info": {"title": title}, "paths": {}}


EXTRA_SOURCES = [
    DocSource("test.a1", "A1", _doc("A1"), category="cat_a", app="app_1"),
    DocSource("test.a2", "A2", _doc("A2"), category="cat_a", app="app_2"),
    DocSource("test.b1", "B1", _doc("B1"), category="cat_b"),
    # Restricted source
    DocSource(
        "test.b2", "B2", _doc("B2"), category="cat_b", groups=("base.group_system",)
    ),
    # Restricted category (see `_openapi_doc_category_groups` patch)
    DocSource("test.c1", "C1", _doc("C1"), category="cat_c"),
]


class OpenApiTestController(http.Controller, OpenApiDocsControllerMixin):
    @http.route(
        f"{ROUTE}/documented/<int:id>",
        type="http",
        auth="public",
        methods=["GET"],
        api_doc={"group": GROUP, "summary": "Documented route"},
    )
    def documented(self, id):
        return str(id)

    @http.route(f"{ROUTE}/undocumented", type="http", auth="public")
    def undocumented(self):
        return ""

    def _test_sources(self):
        ir_http = http.request.env["ir.http"].sudo()
        return (
            ir_http._openapi_doc_sources_for(category="cat_a")
            + ir_http._openapi_doc_sources_for(category="cat_b")
            + ir_http._openapi_doc_sources_for(category="cat_c")
        )

    @http.route(f"{ROUTE}/docs", type="http", auth="public", methods=["GET"])
    def docs(self, category=None, app=None):
        return self._openapi_index_response(
            self._test_sources(),
            f"{ROUTE}/docs",
            lambda source: f"{ROUTE}/docs/{source.key}.json",
            category=category,
            app=app,
        )

    @http.route(
        f"{ROUTE}/docs/<string:key>.json", type="http", auth="public", methods=["GET"]
    )
    def doc(self, key):
        return self._openapi_document_response(self._test_sources(), key)

    @http.route(f"{ROUTE}/routes/<string:key>.json", type="http", auth="public")
    def routes_doc(self, key):
        sources = http.request.env["ir.http"].sudo()._openapi_doc_sources_for("routes")
        return self._openapi_document_response(sources, key)


@tagged("-at_install", "post_install")
class TestHttp(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.registry.clear_cache("routing")
        viewer = "base.group_user,openapi_doc_base.group_openapi_doc_viewer"
        new_test_user(
            cls.env, login="openapi_user", password="openapi_user", groups=viewer
        )
        new_test_user(cls.env, login="internal", password="internal")
        ir_http_cls = type(cls.env["ir.http"])
        orig = ir_http_cls._openapi_doc_sources

        def _sources(self):
            return orig(self) + EXTRA_SOURCES

        def _category_groups(self):
            return {"cat_c": ("base.group_system",)}

        for name, func in (
            ("_openapi_doc_sources", _sources),
            ("_openapi_doc_category_groups", _category_groups),
        ):
            patcher = mock.patch.object(ir_http_cls, name, func)
            patcher.start()
            cls.addClassCleanup(patcher.stop)

    def setUp(self):
        super().setUp()
        self.authenticate("openapi_user", "openapi_user")

    def test_index_all(self):
        """The index lists the sources, w/ the category selector."""
        response = self.url_open(f"{ROUTE}/docs")
        self.assertEqual(response.status_code, 200)
        for key in ("test.a1", "test.a2", "test.b1"):
            self.assertIn(f"{ROUTE}/docs/{key}.json", response.text)
        # category selector shown, app selector not (no category selected: 2 apps)
        self.assertIn("category=cat_b", response.text)

    def test_index_category_app(self):
        """Filtering by category and app narrows the listed sources."""
        response = self.url_open(f"{ROUTE}/docs?category=cat_a")
        self.assertIn("test.a1.json", response.text)
        self.assertIn("test.a2.json", response.text)
        self.assertNotIn("test.b1.json", response.text)
        self.assertIn("app=app_2", response.text)
        response = self.url_open(f"{ROUTE}/docs?category=cat_a&app=app_2")
        self.assertNotIn("test.a1.json", response.text)
        self.assertIn("test.a2.json", response.text)

    def test_document(self):
        """A source's document is served; unknown keys give a 404."""
        response = self.url_open(f"{ROUTE}/docs/test.a1.json")
        self.assertEqual(response.json()["info"]["title"], "A1")
        # Unknown key, or key not served by this controller
        self.assertEqual(self.url_open(f"{ROUTE}/docs/nope.json").status_code, 404)
        response = self.url_open(f"{ROUTE}/docs/routes.{GROUP}.json")
        self.assertEqual(response.status_code, 404)

    def test_routes_source(self):
        """A routes source documents the routes of its group."""
        response = self.url_open(f"{ROUTE}/routes/routes.{GROUP}.json")
        spec = response.json()
        self.assertEqual(list(spec["paths"]), [f"{ROUTE}/documented/{{id}}"])

    def test_access(self):
        """Anonymous users and users w/o the viewer group get a 404."""
        self.authenticate(None, None)
        self.assertEqual(self.url_open(f"{ROUTE}/docs").status_code, 404)
        self.assertEqual(self.url_open(f"{ROUTE}/docs/test.a1.json").status_code, 404)
        # Internal users need the viewer group
        self.authenticate("internal", "internal")
        self.assertEqual(self.url_open(f"{ROUTE}/docs").status_code, 404)

    def test_access_groups(self):
        """Restricted sources and categories show only to users in their groups."""
        # Restricted source and category are hidden to viewers
        response = self.url_open(f"{ROUTE}/docs")
        self.assertIn("test.b1.json", response.text)
        self.assertNotIn("test.b2.json", response.text)
        self.assertNotIn("test.c1.json", response.text)
        self.assertNotIn("category=cat_c", response.text)
        for key in ("test.b2", "test.c1"):
            response = self.url_open(f"{ROUTE}/docs/{key}.json")
            self.assertEqual(response.status_code, 404)
        # ... and visible to admins (implied viewer group)
        self.authenticate("admin", "admin")
        response = self.url_open(f"{ROUTE}/docs")
        self.assertIn("test.b2.json", response.text)
        self.assertIn("test.c1.json", response.text)

    def test_unprotected_source(self):
        """A source must be protected by groups."""
        with self.assertRaises(ValueError):
            DocSource("nope", "Nope", _doc("Nope"), groups=())

    def test_servers(self):
        """The server selector lists the current domain, then the configured URLs."""
        param = self.env["ir.config_parameter"].sudo()
        param.set_param("web.base.url", "http://internal:8069/")
        param.set_param(
            "openapi_doc_base.server_urls",
            "https://erp.example.com, http://internal:8069,",
        )
        self.assertEqual(
            self.env["ir.http"]._openapi_server_urls(),
            [
                ("web.base.url", "http://internal:8069"),
                ("https://erp.example.com", "https://erp.example.com"),
            ],
        )
        response = self.url_open(f"{ROUTE}/docs")
        # The current domain is the default choice, then the configured ones
        self.assertIn('id="o_openapi_server"', response.text)
        self.assertIn('<option value="" class="o_openapi_server_page">', response.text)
        self.assertIn('value="http://internal:8069"', response.text)
        self.assertIn('value="https://erp.example.com"', response.text)

    def test_server_interceptor(self):
        """In the browser, "Try it out" uses the page URL or the selected server."""
        self.env["ir.config_parameter"].sudo().set_param(
            "openapi_doc_base.server_urls", "https://erp.example.com"
        )
        code = """
            const select = document.getElementById("o_openapi_server");
            const intercept = window.ui.getConfigs().requestInterceptor;
            const url = window.location.origin + "/my/api?a=1";
            if (intercept({url}).url !== url) {
                throw new Error("The page URL must be used by default");
            }
            select.value = "https://erp.example.com";
            if (intercept({url}).url !== "https://erp.example.com/my/api?a=1") {
                throw new Error("The selected server must be used");
            }
            if (intercept({url, loadSpec: true}).url !== url) {
                throw new Error("Documents must be loaded from the page");
            }
            console.log("test successful");
        """
        self.browser_js(
            f"{ROUTE}/docs",
            code,
            ready="!!window.ui",
            login="openapi_user",
        )
