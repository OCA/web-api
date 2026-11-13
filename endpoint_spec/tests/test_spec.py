# Copyright 2026 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.tests.common import BaseCase

from ..spec import EndpointSpec, find_spec
from .common import Service, ServiceChild


class TestSpec(BaseCase):
    def test_merge(self):
        """`routing` values are merged, other values are replaced."""
        spec = EndpointSpec(output="a", routing={"auth": "user", "cors": "*"})
        merged = spec.merge(output="b", routing={"auth": "public"})
        self.assertEqual(merged.output, "b")
        self.assertEqual(merged.routing, {"auth": "public", "cors": "*"})
        self.assertEqual(spec.output, "a")

    def test_inherited_spec(self):
        """Child classes inherit the specs of their parents and extend them."""
        self.assertEqual(find_spec(ServiceChild, "scan").input, "in")
        spec = find_spec(ServiceChild, "multi")
        self.assertEqual(spec.output, "out2")
        self.assertEqual(spec.routing, {"api_doc": {"tags": ["child"]}})
        self.assertEqual(find_spec(Service, "multi").output, None)
        self.assertIsNone(find_spec(ServiceChild, "not_decorated"))
