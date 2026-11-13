# Copyright 2026 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.tests.common import BaseCase

from ..conventions import Conventions, collect_endpoints
from ..spec import EndpointSpec
from .common import Base, Service, ServiceChild, routes


class TestConventions(BaseCase):
    def test_collect_explicit_only(self):
        """Only decorated methods are collected, w/ default routes completed."""
        specs = collect_endpoints(Service)
        self.assertEqual(sorted(specs), ["get", "multi", "scan"])
        self.assertEqual(
            specs["get"].routes, routes((("/<int:id>", "/<int:id>/get"), ("GET",)))
        )
        self.assertEqual(specs["scan"].routes, routes((("/scan",), ("POST",))))
        self.assertEqual(specs["multi"].routes, routes((("/multi",), ("GET", "POST"))))

    def test_collect_inherited(self):
        """Child classes get the specs of their parents, extended."""
        specs = collect_endpoints(ServiceChild)
        self.assertEqual(specs["scan"].input, "in")
        self.assertEqual(specs["multi"].output, "out2")
        self.assertEqual(specs["multi"].routes, routes((("/multi",), ("GET", "POST"))))

    def test_custom_conventions(self):
        """Conventions can expose undecorated methods; explicit specs win."""

        class ExposeAll(Conventions):
            """Expose every public method not inherited from `Base`."""

            def guess(self, cls, name, func):
                if hasattr(Base, name):
                    return None
                return EndpointSpec(methods=("PUT",))

        specs = collect_endpoints(Service, conventions=ExposeAll())
        self.assertEqual(sorted(specs), ["get", "multi", "not_decorated", "scan"])
        self.assertNotIn("helper", specs)
        self.assertEqual(
            specs["not_decorated"].routes, routes((("/not_decorated",), ("PUT",)))
        )
        # Explicit specs are not affected by conventions
        self.assertEqual(specs["scan"].routes, routes((("/scan",), ("POST",))))
