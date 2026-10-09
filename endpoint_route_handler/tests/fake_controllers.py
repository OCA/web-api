# Copyright 2022 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import http

from ..utils import make_endpoint


class CTRLFake(http.Controller):
    # Shortcut for dotted path
    _path = "odoo.addons.endpoint_route_handler.tests.fake_controllers.CTRLFake"

    def handler1(self, arg1, arg2=2):
        return arg1, arg2

    def handler2(self, arg1, arg2=2):
        return arg1, arg2

    def custom_handler(self, custom=None):
        return f"Got: {custom}"


class TestController(http.Controller):
    _path = "odoo.addons.endpoint_route_handler.tests.fake_controllers.TestController"

    def _do_something1(self, foo=None):
        body = f"Got: {foo}"
        return http.request.make_response(body)

    def _do_something2(self, default_arg, foo=None):
        body = f"{default_arg} -> got: {foo}"
        return http.request.make_response(body)


class GeneratorFake:
    """Fake routes generator."""

    _path = "odoo.addons.endpoint_route_handler.tests.fake_controllers.GeneratorFake"

    def generate(self, rule, *names, methods=("GET",)):
        for name in names:
            route = f"{rule.route}/{name}"
            routing = {
                "routes": [route],
                "auth": "public",
                "methods": list(methods),
                "csrf": False,
            }
            yield route, make_endpoint(self.handle, routing, pargs=(name,))

    def handle(self, name, **kw):
        return http.request.make_response(f"Generated: {name}")

    def broken(self, rule):
        raise ValueError("Boom")
