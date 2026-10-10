# Copyright 2026 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.tests.common import BaseCase

from ..endpoint import (
    Conventions,
    EndpointRoute,
    EndpointSpec,
    collect_endpoints,
    endpoint,
    find_spec,
)


class Base:
    def helper(self):
        """Public method of the base class: never exposed by conventions."""

    @property
    def boom(self):
        raise AssertionError("Properties must not be evaluated")


class Service(Base):
    @endpoint("GET", path=["/<int:id>", "/<int:id>/get"], auth="public")
    def get(self, id):
        return id

    @endpoint(input="in", output="out")
    def scan(self, barcode):
        return barcode

    @endpoint(["GET", "POST"])
    def multi(self):
        return True

    def not_decorated(self):
        return True

    def _private(self):
        return True


class ServiceChild(Service):
    def scan(self, barcode):
        return super().scan(barcode)

    @endpoint.extend(routing={"api_doc": {"tags": ["child"]}}, output="out2")
    def multi(self):
        return super().multi()


def _routes(*pairs):
    return tuple(EndpointRoute(paths=tuple(p), methods=tuple(m)) for p, m in pairs)


class TestEndpoint(BaseCase):
    def test_decorator_does_not_wrap(self):
        """The decorator only attaches metadata: the method is left as is."""
        self.assertEqual(Service().scan("abc"), "abc")
        self.assertEqual(Service.scan.__name__, "scan")

    def test_collect_explicit_only(self):
        """Only decorated methods are collected, w/ their routes and routing."""
        specs = collect_endpoints(Service)
        self.assertEqual(sorted(specs), ["get", "multi", "scan"])
        self.assertEqual(
            specs["get"].routes, _routes((("/<int:id>", "/<int:id>/get"), ("GET",)))
        )
        self.assertEqual(specs["get"].routing, {"auth": "public"})
        self.assertEqual(specs["scan"].routes, _routes((("/scan",), ("POST",))))
        self.assertEqual(specs["scan"].input, "in")
        self.assertEqual(specs["multi"].routes, _routes((("/multi",), ("GET", "POST"))))

    def test_inherited_spec(self):
        """Child classes inherit the specs of their parents and extend them."""
        specs = collect_endpoints(ServiceChild)
        self.assertEqual(specs["scan"].input, "in")
        self.assertEqual(specs["multi"].output, "out2")
        self.assertEqual(specs["multi"].routing, {"api_doc": {"tags": ["child"]}})
        self.assertEqual(specs["multi"].routes, _routes((("/multi",), ("GET", "POST"))))
        self.assertIsNone(find_spec(ServiceChild, "not_decorated"))

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
            specs["not_decorated"].routes, _routes((("/not_decorated",), ("PUT",)))
        )
        # Explicit specs are not affected by conventions
        self.assertEqual(specs["scan"].routes, _routes((("/scan",), ("POST",))))
