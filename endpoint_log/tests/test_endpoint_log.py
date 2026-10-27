# Copyright 2026 Quartile (https://www.quartile.co)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import os
import unittest

from odoo.tools import mute_logger

from .common import Common


@unittest.skipIf(os.getenv("SKIP_HTTP_CASE"), "TestEndpointLog skipped")
class TestEndpointLog(Common):
    def test_no_log_if_disabled(self):
        self.endpoint_ok.log_requests = False
        with self.log_capturer(self.endpoint_ok) as capturer:
            response = self.url_open("/endpoint_log/test/ok")
            self.assertEqual(response.status_code, 200)
        self.assertFalse(capturer.records)
        self.assertNotIn("API-Log-Entry-ID", response.headers)

    def test_log_simple(self):
        with self.log_capturer(self.endpoint_ok) as capturer:
            response = self.url_open("/endpoint_log/test/ok")
            self.assertEqual(response.status_code, 200)
        self.assertEqual(len(capturer.records), 1)
        log = capturer.records
        self.assertEqual(response.headers["API-Log-Entry-ID"], str(log.id))
        self.assertTrue(log.request_url.endswith("/endpoint_log/test/ok"))
        self.assertEqual(log.request_method, "GET")
        self.assertEqual(log.response_status_code, 200)
        self.assertEqual(json.loads(log.response_body), {"name": "Endpoint Log User"})
        self.assertTrue(log.time > 0)
        self.assertFalse(log.stack_trace)
        # ``collection_ref`` is matched by ``log_capturer``. Its derived
        # ``collection_model`` and ``collection_id`` cannot be checked here: the
        # endpoint is not committed, so the log cursor cannot resolve it.

    def test_log_post_body(self):
        payload = {"items": [1, 2, 3]}
        with self.log_capturer(self.endpoint_post) as capturer:
            response = self.url_open(
                "/endpoint_log/test/post",
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
            )
            self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), payload)
        log = capturer.records
        self.assertEqual(log.request_method, "POST")
        self.assertEqual(json.loads(log.request_body), payload)
        self.assertEqual(json.loads(log.response_body), payload)

    @mute_logger("odoo.http", "endpoint.endpoint")
    def test_log_request_validation_error(self):
        # Rejected by ``_validate_request`` before the endpoint's code runs
        with self.log_capturer(self.endpoint_schema) as capturer:
            response = self.url_open(
                "/endpoint_log/test/schema",
                data=json.dumps({"items": "not a list"}),
                headers={"Content-Type": "application/json"},
            )
            self.assertEqual(response.status_code, 400)
        log = capturer.records
        self.assertEqual(len(log), 1)
        self.assertEqual(log.response_status_code, 400)
        self.assertEqual(json.loads(log.response_body), response.json())
        self.assertIn("RequestValidationError", log.stack_trace)

    @mute_logger("odoo.http", "endpoint.endpoint")
    def test_log_user_error(self):
        with self.log_capturer(self.endpoint_user_error) as capturer:
            response = self.url_open("/endpoint_log/test/user_error")
            self.assertEqual(response.status_code, 400)
        log = capturer.records
        self.assertEqual(len(log), 1)
        self.assertEqual(log.response_status_code, 400)
        self.assertTrue(log.time > 0)
        # The original error is chained to the BadRequest raised by the endpoint
        self.assertIn(
            "odoo.exceptions.ValidationError: Sorry, not allowed", log.stack_trace
        )
        self.assertIn("werkzeug.exceptions.BadRequest", log.stack_trace)

    @mute_logger("odoo.http")
    def test_log_bare_error(self):
        with self.log_capturer(self.endpoint_bare_error) as capturer:
            response = self.url_open("/endpoint_log/test/bare_error")
            self.assertEqual(response.status_code, 500)
        log = capturer.records
        self.assertEqual(len(log), 1)
        self.assertEqual(log.response_status_code, 500)
        self.assertIn("ZeroDivisionError: division by zero", log.stack_trace)
