# Copyright 2026 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.tests.common import BaseCase

from ..spec import find_spec
from .common import Service, routes


class TestDecorator(BaseCase):
    def test_decorator_does_not_wrap(self):
        """The decorator only attaches metadata: the method is left as is."""
        self.assertEqual(Service().scan("abc"), "abc")
        self.assertEqual(Service.scan.__name__, "scan")

    def test_spec_values(self):
        """Path, methods, params and routing keys end up in the spec."""
        spec = find_spec(Service, "get")
        self.assertEqual(
            spec.routes, routes((("/<int:id>", "/<int:id>/get"), ("GET",)))
        )
        self.assertEqual(spec.routing, {"auth": "public"})
        spec = find_spec(Service, "scan")
        self.assertEqual((spec.input, spec.output), ("in", "out"))
        self.assertEqual(spec.routes, ())
