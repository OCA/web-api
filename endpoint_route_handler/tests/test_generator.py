# Copyright 2026 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from unittest import mock

from odoo.tests.common import HttpCase, TransactionCase, tagged
from odoo.tools import mute_logger

from odoo.addons.endpoint_route_handler.exceptions import EndpointHandlerNotFound
from odoo.addons.endpoint_route_handler.registry import EndpointRegistry
from odoo.addons.endpoint_route_handler.utils import make_endpoint

from .fake_controllers import CTRLFake, GeneratorFake

GROUP = "test_route_generator"


def _generator_options(method_name="generate", pargs=("one", "two"), **kw):
    opts = {
        "klass_dotted_path": GeneratorFake._path,
        "method_name": method_name,
        "default_pargs": list(pargs),
    }
    opts.update(kw)
    return {"generator": opts}


class GeneratorMixin:
    @classmethod
    def _make_generator_rule(cls, key="gen1", route="/gen", options=None):
        return cls.reg.make_rule(
            key,
            route,
            options or _generator_options(),
            # The routing of the anchor rule is not loaded as is,
            # but generators can use it as base.
            {"routes": [route], "type": "http", "auth": "public"},
            f"hash-{key}",
            route_group=GROUP,
        )


@tagged("-at_install", "post_install")
class TestGenerator(TransactionCase, GeneratorMixin):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.reg = EndpointRegistry.registry_for(cls.env.cr)

    def test_options_validation(self):
        handler = {"klass_dotted_path": CTRLFake._path, "method_name": "handler1"}
        with self.assertRaises(AssertionError):
            self._make_generator_rule(
                options=dict(_generator_options(), handler=handler)
            )
        with self.assertRaises(AssertionError):
            self._make_generator_rule(options={"generator": {"method_name": "x"}})
        rule = self._make_generator_rule()
        self.assertTrue(rule.is_generator)

    def test_drop_no_rules(self):
        self.assertTrue(self.reg.drop_rules([]))

    def test_make_endpoint(self):
        endpoint = make_endpoint(
            CTRLFake().handler1, {"routes": ["/foo"]}, pargs=("one",)
        )
        self.assertEqual(endpoint(), ("one", 2))
        self.assertEqual(endpoint.routing["type"], "http")
        self.assertEqual(endpoint.routing["auth"], "user")
        self.assertIs(endpoint.routing["readonly"], False)
        self.assertIsNone(endpoint.routing["methods"])
        with self.assertRaisesRegex(ValueError, "No route"):
            make_endpoint(CTRLFake().handler1, {"routes": []})
        with self.assertRaisesRegex(ValueError, "Unknown routing type"):
            make_endpoint(CTRLFake().handler1, {"routes": ["/a"], "type": "nope"})

    def test_generator_python(self):
        rule = self._make_generator_rule()
        with self.assertRaises(ValueError):
            rule.endpoint  # pylint: disable=pointless-statement # noqa: B018
        res = list(rule.iter_routing_rules(self.env))
        self.assertEqual([url for url, __ in res], ["/gen/one", "/gen/two"])
        __, endpoint = res[0]
        self.assertEqual(endpoint.routing["methods"], ["GET"])
        self.assertEqual(endpoint.routing["routes"], ["/gen/one"])

    def test_generator_model(self):
        users_cls = type(self.env["res.users"])
        calls = []

        def _fake_generate(records, rule, *names):
            calls.append((records, names))
            yield from GeneratorFake().generate(rule, *names)

        options = {
            "generator": {
                "model": "res.users",
                "res_id": self.env.user.id,
                "method_name": "_test_generate_routes",
                "default_pargs": ["three"],
            }
        }
        rule = self._make_generator_rule(options=options)
        with mock.patch.object(
            users_cls, "_test_generate_routes", _fake_generate, create=True
        ):
            res = list(rule.iter_routing_rules(self.env))
        self.assertEqual([url for url, __ in res], ["/gen/three"])
        records, names = calls[0]
        self.assertEqual(records, self.env.user)
        self.assertTrue(records.env.su)
        self.assertEqual(names, ("three",))

    def test_generator_model_not_found(self):
        options = {"generator": {"model": "nope.nope", "method_name": "x"}}
        rule = self._make_generator_rule(options=options)
        with self.assertRaises(EndpointHandlerNotFound):
            list(rule.iter_routing_rules(self.env))
        options = {"generator": {"model": "res.users", "method_name": "_nope_"}}
        rule = self._make_generator_rule(options=options)
        with self.assertRaises(EndpointHandlerNotFound):
            list(rule.iter_routing_rules(self.env))

    def test_routing_rules_skip_broken_generator(self):
        EndpointRegistry.wipe_registry_for(self.env.cr)
        good = self._make_generator_rule()
        broken = self._make_generator_rule(
            key="gen2", route="/broken", options=_generator_options("broken", ())
        )
        self.reg.update_rules([good, broken])
        with mute_logger("odoo.addons.endpoint_route_handler.models.ir_http"):
            urls = [url for url, __ in self.env["ir.http"]._endpoint_routing_rules()]
        self.assertIn("/gen/one", urls)
        self.assertIn("/gen/two", urls)
        self.assertFalse([x for x in urls if x.startswith("/broken")])


@tagged("-at_install", "post_install")
class TestGeneratorHttp(HttpCase, GeneratorMixin):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.reg = EndpointRegistry.registry_for(cls.env.cr)
        cls.reg.update_rules([cls._make_generator_rule(route="/test_generator")])
        cls.env.registry.clear_cache("routing")

    def test_generated_routes_served(self):
        for name in ("one", "two"):
            response = self.url_open(f"/test_generator/{name}")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.text, f"Generated: {name}")

    def test_generated_routes_method(self):
        response = self.url_open("/test_generator/one", data={"a": 1})
        self.assertEqual(response.status_code, 405)

    def test_anchor_route_not_served(self):
        response = self.url_open("/test_generator")
        self.assertEqual(response.status_code, 404)

    def test_routing_map_wo_request(self):
        # The routing map can be built outside of a request (eg: tests, scripts)
        self.reg.update_rules([self._make_generator_rule()])
        self.env.registry.clear_cache("routing")
        urls = [r.rule for r in self.env["ir.http"].routing_map().iter_rules()]
        self.assertIn("/gen/one", urls)
