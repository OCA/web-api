# Copyright 2021 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
import hashlib
import json
from contextlib import contextmanager
from unittest.mock import patch

import odoo
from odoo.tools import mute_logger

from ..registry import EndpointRegistry
from .common import CommonEndpoint
from .fake_controllers import CTRLFake


@contextmanager
def new_rollbacked_env():
    # Borrowed from `component`
    registry = odoo.modules.registry.Registry(odoo.tests.common.get_db_name())
    uid = odoo.SUPERUSER_ID
    cr = registry.cursor()
    try:
        yield odoo.api.Environment(cr, uid, {})
    finally:
        cr.rollback()  # we shouldn't have to commit anything
        cr.close()


def make_new_route(env, **kw):
    model = env["endpoint.route.handler.tool"]
    vals = {
        "name": "Test custom route",
        "route": "/my/test/route",
        "request_method": "GET",
    }
    vals.update(kw)
    new_route = model.new(vals)
    return new_route


class TestEndpoint(CommonEndpoint):
    def tearDown(self):
        EndpointRegistry.wipe_registry_for(self.env.cr)
        super().tearDown()

    def test_routing_map_no_request(self):
        """The routing map builds w/o a bound request (crons, shell, tests)."""
        # Crons, `odoo shell` and core tests build the routing map with no
        # request bound. website's TestWebsiteTechnicalPage does, through
        # website.technical.page.get_static_routes(). No mocked request here
        # on purpose.
        self.env.registry.clear_cache("routing")
        self.assertTrue(self.env["ir.http"].routing_map())

    def test_endpoint_hash_stable(self):
        """The hash is a md5 of the routing values: the same in every process."""
        new_route = make_new_route(self.env)
        values = {
            fname: new_route[fname] for fname in new_route._routing_impacting_fields()
        }
        # Same as computed in any other process: plain md5 of the values
        data = json.dumps(values, sort_keys=True, default=str)
        expected = hashlib.md5(data.encode(), usedforsecurity=False).hexdigest()
        self.assertEqual(new_route.endpoint_hash, expected)
        self.assertEqual(len(new_route.endpoint_hash), 32)

    def test_consumer_models_exclude_tool(self):
        """Transient tools are not consumers: their routes are never synced."""
        models = self.env[
            "endpoint.route.handler"
        ]._find_endpoint_route_consumer_models()
        self.assertNotIn("endpoint.route.handler.tool", models)

    def test_as_tool_base_data(self):
        """Changing the route of a tool changes its hash."""
        new_route = make_new_route(self.env)
        self.assertEqual(new_route.route, "/my/test/route")
        first_hash = new_route.endpoint_hash
        self.assertTrue(first_hash)
        new_route.route += "/new"
        self.assertNotEqual(new_route.endpoint_hash, first_hash)

    def test_route_field_precomputed(self):
        """Regression guard: ensure ``precompute=True`` stays on ``route``.

        Without it, downstream modules that derive ``route`` via compute
        would hit a "Missing required value" error at INSERT time.
        """
        Model = type(self.env["endpoint.route.handler.tool"])

        def _fake_compute_route(self):
            for rec in self:
                rec.route = "/precompute/probe"

        with patch.object(Model, "_compute_route", _fake_compute_route):
            rec = self.env["endpoint.route.handler.tool"].create(
                {
                    "name": "Precompute test",
                    "request_method": "GET",
                }
            )
            self.assertEqual(rec.route, "/precompute/probe")

    @mute_logger("odoo.addons.base.models.ir_http")
    def test_as_tool_register_single_controller(self):
        """A registered tool is served at its route, and follows route changes."""
        new_route = make_new_route(self.env)
        options = {
            "handler": {
                "klass_dotted_path": CTRLFake._path,
                "method_name": "custom_handler",
            }
        }

        with self._get_mocked_request():
            new_route._register_single_controller(options=options, init=True)
            # Ensure the routing rule is registered
            rmap = self.env["ir.http"].routing_map()
            self.assertIn("/my/test/route", [x.rule for x in rmap._rules])

        # Ensure is updated when needed
        new_route.route += "/new"
        with self._get_mocked_request():
            new_route._register_single_controller(options=options, init=True)
            rmap = self.env["ir.http"].routing_map()
            self.assertNotIn("/my/test/route", [x.rule for x in rmap._rules])
            self.assertIn("/my/test/route/new", [x.rule for x in rmap._rules])

    @mute_logger("odoo.addons.base.models.ir_http")
    def test_as_tool_register_controllers(self):
        """Registered tools are served at their route, and follow route changes."""
        new_route = make_new_route(self.env)
        options = {
            "handler": {
                "klass_dotted_path": CTRLFake._path,
                "method_name": "custom_handler",
            }
        }

        with self._get_mocked_request():
            new_route._register_controllers(options=options, init=True)
            # Ensure the routing rule is registered
            rmap = self.env["ir.http"].routing_map()
            self.assertIn("/my/test/route", [x.rule for x in rmap._rules])

        # Ensure is updated when needed
        new_route.route += "/new"
        with self._get_mocked_request():
            new_route._register_controllers(options=options, init=True)
            rmap = self.env["ir.http"].routing_map()
            self.assertNotIn("/my/test/route", [x.rule for x in rmap._rules])
            self.assertIn("/my/test/route/new", [x.rule for x in rmap._rules])

    @mute_logger("odoo.addons.base.models.ir_http")
    def test_as_tool_register_controllers_dynamic_route(self):
        """A route w/ a model converter is registered as given."""
        route = "/my/app/<model(app.model):foo>"
        new_route = make_new_route(self.env, route=route)
        options = {
            "handler": {
                "klass_dotted_path": CTRLFake._path,
                "method_name": "custom_handler",
            }
        }

        with self._get_mocked_request():
            new_route._register_controllers(options=options, init=True)
            # Ensure the routing rule is registered
            rmap = self.env["ir.http"].routing_map()
            self.assertIn(route, [x.rule for x in rmap._rules])


class TestEndpointCrossEnv(CommonEndpoint):
    def setUp(self):
        super().setUp()
        EndpointRegistry.wipe_registry_for(self.env.cr)

    @mute_logger("odoo.addons.base.models.ir_http", "odoo.modules.registry")
    def test_cross_env_consistency(self):
        """Ensure route updates are propagated to all envs."""
        route = "/my/app/<model(app.model):foo>"
        new_route = make_new_route(self.env, route=route)
        options = {
            "handler": {
                "klass_dotted_path": CTRLFake._path,
                "method_name": "custom_handler",
            }
        }

        env1 = self.env
        reg = EndpointRegistry.registry_for(self.env.cr)
        new_route._register_controllers(options=options)

        last_version0 = reg.last_version()
        with self._get_mocked_request():
            with new_rollbacked_env() as env2:
                # Load maps
                env1["ir.http"].routing_map()
                env2["ir.http"].routing_map()
                self.assertEqual(
                    env1["ir.http"]._endpoint_route_last_version(), last_version0
                )
                self.assertEqual(
                    env2["ir.http"]._endpoint_route_last_version(), last_version0
                )
                rmap = self.env["ir.http"].routing_map()
                self.assertIn(route, [x.rule for x in rmap._rules])
                rmap = env2["ir.http"].routing_map()
                self.assertIn(route, [x.rule for x in rmap._rules])

                # add new route
                route = "/my/new/<model(app.model):foo>"
                new_route = make_new_route(self.env, route=route)
                new_route._register_controllers(options=options)

                rmap = self.env["ir.http"].routing_map()
                self.assertIn(route, [x.rule for x in rmap._rules])
                rmap = env2["ir.http"].routing_map()
                self.assertIn(route, [x.rule for x in rmap._rules])
                self.assertTrue(
                    env1["ir.http"]._endpoint_route_last_version() > last_version0
                )
                self.assertTrue(
                    env2["ir.http"]._endpoint_route_last_version() > last_version0
                )

    # TODO: test unregister
