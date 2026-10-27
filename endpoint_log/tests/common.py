# Copyright 2026 Quartile (https://www.quartile.co)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import threading
from contextlib import contextmanager

from odoo.tests.common import RecordCapturer
from odoo.tests.test_cursor import TestCursor

from odoo.addons.api_log.tests.common import Common as CommonAPILog


class Common(CommonAPILog):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        demo_user = cls.env["res.users"].create(
            {"login": "endpoint_log_user", "name": "Endpoint Log User"}
        )
        vals = {
            "request_method": "GET",
            "auth_type": "public",
            "exec_as_user_id": demo_user.id,
            "exec_mode": "code",
            "log_requests": True,
        }
        Endpoint = cls.env["endpoint.endpoint"]
        cls.endpoint_ok = Endpoint.create(
            dict(
                vals,
                name="Log OK",
                route="/endpoint_log/test/ok",
                code_snippet='result = {"payload": {"name": user.name}}',
            )
        )
        cls.endpoint_post = Endpoint.create(
            dict(
                vals,
                name="Log POST",
                route="/endpoint_log/test/post",
                request_method="POST",
                request_content_type="application/json",
                code_snippet='result = {"payload": request.get_json_data()}',
            )
        )
        cls.endpoint_schema = Endpoint.create(
            dict(
                vals,
                name="Log schema",
                route="/endpoint_log/test/schema",
                request_method="POST",
                request_content_type="application/json",
                request_content_schema=(
                    "type: object\nproperties:\n  items:\n    type: array\n"
                ),
                code_snippet='result = {"payload": {"ok": True}}',
            )
        )
        cls.endpoint_user_error = Endpoint.create(
            dict(
                vals,
                name="Log user error",
                route="/endpoint_log/test/user_error",
                code_snippet='raise exceptions.ValidationError("Sorry, not allowed")',
            )
        )
        cls.endpoint_bare_error = Endpoint.create(
            dict(
                vals,
                name="Log bare error",
                route="/endpoint_log/test/bare_error",
                code_snippet="result = 1 / 0",
            )
        )
        cls.endpoints = (
            cls.endpoint_ok
            | cls.endpoint_post
            | cls.endpoint_schema
            | cls.endpoint_user_error
            | cls.endpoint_bare_error
        )
        cls.endpoints._handle_registry_sync()

    def setUp(self):
        super().setUp()
        # Use a side test cursor to be able to get exception logs
        reg = self.env.registry
        reg.test_log_lock = threading.RLock()
        reg.test_log_cr = TestCursor(reg._db.cursor(), reg.test_log_lock, False)

    def tearDown(self):
        reg = self.env.registry
        reg.test_log_cr.rollback()
        reg.test_log_cr.close()
        # Also close the real cursor to avoid unclosed errors
        reg.test_log_cr._cursor.close()
        reg.test_log_cr = None
        reg.test_log_lock = None
        # Clear cache for method ``ir.http.routing_map()``
        reg.clear_cache("routing")
        super().tearDown()

    @contextmanager
    def log_capturer(self, endpoint):
        log_env = self.env(cr=self.env.registry.test_log_cr)
        with RecordCapturer(
            log_env[self.log_model._name],
            [("collection_ref", "=", f"{endpoint._name},{endpoint.id}")],
        ) as capturer:
            yield capturer
