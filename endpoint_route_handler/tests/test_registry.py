# Copyright 2021 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from psycopg2 import DatabaseError

from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger

from odoo.addons.endpoint_route_handler.exceptions import EndpointHandlerNotFound
from odoo.addons.endpoint_route_handler.registry import EndpointRegistry

from .fake_controllers import CTRLFake


@tagged("-at_install", "post_install")
class TestRegistry(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.reg = EndpointRegistry.registry_for(cls.env.cr)

    def setUp(self):
        super().setUp()
        EndpointRegistry.wipe_registry_for(self.env.cr)

    def tearDown(self):
        EndpointRegistry.wipe_registry_for(self.env.cr)
        super().tearDown()

    def _count_rules(self, groups=("test_route_handler",)):
        # NOTE: use alwways groups to filter in your tests
        # because some other module might add rules for testing.
        self.env.cr.execute(
            "SELECT COUNT(id) FROM endpoint_route WHERE route_group IN %s", (groups,)
        )
        return self.env.cr.fetchone()[0]

    def test_registry_empty(self):
        self.assertEqual(list(self.reg.get_rules()), [])
        self.assertEqual(self._count_rules(), 0)

    def test_last_update(self):
        self.assertEqual(self.reg.last_update(), 0.0)
        rule1, rule2 = self._make_rules(stop=3)
        last_update0 = self.reg.last_update()
        self.assertTrue(last_update0 > 0)
        rule1.options = {
            "handler": {
                "klass_dotted_path": CTRLFake._path,
                "method_name": "handler2",
            }
        }
        # FIXME: to test timestamp we have to mock psql datetime.
        # self.reg.update_rules([rule1])
        # last_update1 = self.reg.last_update()
        # self.assertTrue(last_update1 > last_update0)
        # rule2.options = {
        #     "handler": {
        #         "klass_dotted_path": CTRLFake._path,
        #         "method_name": "handler2",
        #     }
        # }
        # self.reg.update_rules([rule2])
        # last_update2 = self.reg.last_update()
        # self.assertTrue(last_update2 > last_update1)

    def test_last_version(self):
        last_version0 = self.reg.last_version()
        self._make_rules(stop=3)
        last_version1 = self.reg.last_version()
        self.assertTrue(last_version1 > last_version0)

    def _make_rules(self, stop=5, start=1, **kw):
        res = []
        for i in range(start, stop):
            key = f"route{i}"
            route = f"/test/{i}"
            options = {
                "handler": {
                    "klass_dotted_path": CTRLFake._path,
                    "method_name": "handler1",
                }
            }
            routing = {"routes": []}
            endpoint_hash = i
            route_group = "test_route_handler"
            rule = self.reg.make_rule(
                key,
                route,
                options,
                routing,
                endpoint_hash,
                route_group=route_group,
            )
            for k, v in kw.items():
                setattr(rule, k, v)
            res.append(rule)
        self.reg.update_rules(res)
        return res

    def test_add_rule(self):
        self._make_rules(stop=5)
        self.assertEqual(self._count_rules(), 4)
        self.assertEqual(self.reg._get_rule("route1").endpoint_hash, "1")
        self.assertEqual(self.reg._get_rule("route2").endpoint_hash, "2")
        self.assertEqual(self.reg._get_rule("route3").endpoint_hash, "3")
        self.assertEqual(self.reg._get_rule("route4").endpoint_hash, "4")

    def test_get_rules(self):
        self._make_rules(stop=4)
        self.assertEqual(self._count_rules(), 3)
        self.assertEqual(
            [x.key for x in self.reg.get_rules()], ["route1", "route2", "route3"]
        )
        self._make_rules(start=10, stop=14)
        self.assertEqual(self._count_rules(), 7)
        self.reg.get_rules()
        self.assertEqual(
            sorted([x.key for x in self.reg.get_rules()]),
            sorted(
                [
                    "route1",
                    "route2",
                    "route3",
                    "route10",
                    "route11",
                    "route12",
                    "route13",
                ]
            ),
        )

    def test_update_rule(self):
        rule1, rule2 = self._make_rules(stop=3)
        self.assertEqual(
            self.reg._get_rule("route1").handler_options.method_name, "handler1"
        )
        self.assertEqual(
            self.reg._get_rule("route2").handler_options.method_name, "handler1"
        )
        rule1.options = {
            "handler": {
                "klass_dotted_path": CTRLFake._path,
                "method_name": "handler2",
            }
        }
        rule2.options = {
            "handler": {
                "klass_dotted_path": CTRLFake._path,
                "method_name": "handler3",
            }
        }
        self.reg.update_rules([rule1, rule2])
        self.assertEqual(
            self.reg._get_rule("route1").handler_options.method_name, "handler2"
        )
        self.assertEqual(
            self.reg._get_rule("route2").handler_options.method_name, "handler3"
        )

    @mute_logger("odoo.sql_db")
    def test_rule_constraints(self):
        rule1, rule2 = self._make_rules(stop=3)
        msg = (
            'duplicate key value violates unique constraint "endpoint_route__key_uniq"'
        )
        with self.assertRaisesRegex(DatabaseError, msg), self.env.cr.savepoint():
            self.reg._create({rule1.key: rule1.to_row()})
        msg = (
            "duplicate key value violates unique constraint "
            '"endpoint_route__endpoint_hash_uniq"'
        )
        with self.assertRaisesRegex(DatabaseError, msg), self.env.cr.savepoint():
            rule2.endpoint_hash = rule1.endpoint_hash
            rule2.key = "key3"
            self.reg._create({rule2.key: rule2.to_row()})

    def test_drop_rule(self):
        rules = self._make_rules(stop=3)
        self.assertEqual(self._count_rules(), 2)
        self.reg.drop_rules([x.key for x in rules])
        self.assertEqual(self._count_rules(), 0)

    def test_endpoint_lookup_ko(self):
        options = {
            "handler": {
                "klass_dotted_path": "no.where.to.be.SeenKlass",
                "method_name": "foo",
            }
        }
        rule = self._make_rules(stop=2, options=options)[0]
        with self.assertRaises(EndpointHandlerNotFound):
            rule.endpoint  # pylint: disable=pointless-statement

    def test_endpoint_lookup_ok(self):
        rule = self._make_rules(stop=2)[0]
        expected = (
            "<bound method CTRLFake.handler1 of "
            "<odoo.addons.endpoint_route_handler.tests.fake_controllers.CTRLFake"
        )
        self.assertTrue(str(rule.endpoint.func).startswith(expected))
        self.assertEqual(rule.endpoint("one"), ("one", 2))

    def test_endpoint_lookup_ok_args(self):
        options = {
            "handler": {
                "klass_dotted_path": CTRLFake._path,
                "method_name": "handler1",
                "default_pargs": ("one",),
            }
        }
        rule = self._make_rules(stop=2, options=options)[0]
        expected = (
            "<bound method CTRLFake.handler1 of "
            "<odoo.addons.endpoint_route_handler.tests.fake_controllers.CTRLFake"
        )
        self.assertTrue(str(rule.endpoint.func).startswith(expected))
        self.assertEqual(rule.endpoint(), ("one", 2))

    def test_get_rule_by_group(self):
        self.assertEqual(self._count_rules(), 0)
        self._make_rules(stop=4, route_group="one")
        self._make_rules(start=5, stop=7, route_group="two")
        self.assertEqual(self._count_rules(groups=("one", "two")), 5)
        rules = self.reg.get_rules_by_group("one")
        self.assertEqual([rule.key for rule in rules], ["route1", "route2", "route3"])
        rules = self.reg.get_rules_by_group("two")
        self.assertEqual([rule.key for rule in rules], ["route5", "route6"])
