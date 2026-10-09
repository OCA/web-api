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


def _generator_options(method_name="generate", names=(), **kw):
    """Options of a rule using `GeneratorFake.<method_name>` w/ `names` as args."""
    opts = {
        "klass_dotted_path": GeneratorFake._path,
        "method_name": method_name,
        "default_pargs": list(names),
    }
    opts.update(kw)
    return {"generator": opts}


class GeneratorMixin:
    @classmethod
    def _make_generator_rule(cls, key="gen1", route="/gen", names=(), options=None):
        """Make a rule (not stored) whose generator yields `<route>/<name>` per name."""
        return cls.reg.make_rule(
            key,
            route,
            options or _generator_options(names=names),
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
        """A rule has either a handler or a generator, and a valid generator."""
        handler = {"klass_dotted_path": CTRLFake._path, "method_name": "handler1"}
        # Both handler and generator
        with self.assertRaises(AssertionError):
            self._make_generator_rule(
                options=dict(_generator_options(), handler=handler)
            )
        # Generator w/o class nor model
        with self.assertRaises(AssertionError):
            self._make_generator_rule(options={"generator": {"method_name": "x"}})
        rule = self._make_generator_rule()
        self.assertTrue(rule.is_generator)

    def test_drop_no_rules(self):
        """Dropping no rules is a no-op (no invalid SQL)."""
        self.assertTrue(self.reg.drop_rules([]))

    def test_make_endpoint(self):
        """Endpoints get the routing keys required by Odoo; invalid routing raises."""
        # `handler1(arg1, arg2=2)`: `pargs` are bound to the endpoint
        endpoint = make_endpoint(
            CTRLFake().handler1, {"routes": ["/foo"]}, pargs=("one",)
        )
        self.assertEqual(endpoint(), ("one", 2))
        # Missing keys are filled w/ defaults
        self.assertEqual(endpoint.routing["type"], "http")
        self.assertEqual(endpoint.routing["auth"], "user")
        self.assertIs(endpoint.routing["readonly"], False)
        self.assertIsNone(endpoint.routing["methods"])
        with self.assertRaisesRegex(ValueError, "No route"):
            make_endpoint(CTRLFake().handler1, {"routes": []})
        with self.assertRaisesRegex(ValueError, "Unknown routing type"):
            make_endpoint(CTRLFake().handler1, {"routes": ["/a"], "type": "nope"})

    def test_generator_python(self):
        """A class generator yields its routes; the rule has no endpoint itself."""
        rule = self._make_generator_rule(route="/gen", names=("one", "two"))
        with self.assertRaises(ValueError):
            rule.endpoint  # pylint: disable=pointless-statement # noqa: B018
        res = list(rule.iter_routing_rules(self.env))
        self.assertEqual([url for url, __ in res], ["/gen/one", "/gen/two"])
        __, endpoint = res[0]
        # Routing set by `GeneratorFake.generate`
        self.assertEqual(endpoint.routing["methods"], ["GET"])
        self.assertEqual(endpoint.routing["routes"], ["/gen/one"])

    def test_generator_model(self):
        """A model generator is called on the record, as sudo, w/ the rule args."""
        users_cls = type(self.env["res.users"])
        calls = []

        def _fake_generate(records, rule, *names):
            calls.append((records, names))
            yield from GeneratorFake().generate(rule, *names)

        # Generator = `res.users(<current user>)._test_generate_routes("three")`
        options = {
            "generator": {
                "model": "res.users",
                "res_id": self.env.user.id,
                "method_name": "_test_generate_routes",
                "default_pargs": ["three"],
            }
        }
        rule = self._make_generator_rule(route="/gen", options=options)
        # Add the generator method on the model
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
        """A missing generator model or method raises EndpointHandlerNotFound."""
        options = {"generator": {"model": "nope.nope", "method_name": "x"}}
        rule = self._make_generator_rule(options=options)
        with self.assertRaises(EndpointHandlerNotFound):
            list(rule.iter_routing_rules(self.env))
        options = {"generator": {"model": "res.users", "method_name": "_nope_"}}
        rule = self._make_generator_rule(options=options)
        with self.assertRaises(EndpointHandlerNotFound):
            list(rule.iter_routing_rules(self.env))

    def test_routing_rules_skip_broken_generator(self):
        """A failing generator is skipped, the others are loaded."""
        EndpointRegistry.wipe_registry_for(self.env.cr)
        good = self._make_generator_rule("gen1", "/gen", names=("one", "two"))
        # `GeneratorFake.broken` raises
        broken = self._make_generator_rule(
            "gen2", "/broken", options=_generator_options("broken")
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
        # Serves GET `/test_generator/one` and `/test_generator/two`
        rule = cls._make_generator_rule(route="/test_generator", names=("one", "two"))
        cls.reg.update_rules([rule])
        cls.env.registry.clear_cache("routing")

    def test_generated_routes_served(self):
        """Generated routes are served by the generated endpoint."""
        for name in ("one", "two"):
            response = self.url_open(f"/test_generator/{name}")
            self.assertEqual(response.status_code, 200)
            # Response of `GeneratorFake.handle(name)`
            self.assertEqual(response.text, f"Generated: {name}")

    def test_generated_routes_method(self):
        """Generated routes only accept their methods (GET here)."""
        # `data` makes it a POST
        response = self.url_open("/test_generator/one", data={"a": 1})
        self.assertEqual(response.status_code, 405)

    def test_anchor_route_not_served(self):
        """The route of the rule itself (the anchor) is not served."""
        response = self.url_open("/test_generator")
        self.assertEqual(response.status_code, 404)

    def test_routing_map_wo_request(self):
        """Generated routes are loaded in a routing map built w/o a request."""
        self.reg.update_rules(
            [self._make_generator_rule("gen2", "/gen", names=("one",))]
        )
        self.env.registry.clear_cache("routing")
        urls = [r.rule for r in self.env["ir.http"].routing_map().iter_rules()]
        self.assertIn("/gen/one", urls)
