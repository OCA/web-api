# Copyright 2025 feihu.zhang
# @author: feihu.zhang <feihu.zhang@live.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import datetime
import os
import unittest

import requests

from odoo import tools
from odoo.tests.common import HttpCase
from odoo.tools.misc import mute_logger


@unittest.skipIf(os.getenv("SKIP_HTTP_CASE"), "EndpointAuthBearerHttpCase skipped")
class EndpointAuthBearerHttpCase(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env.ref("base.user_demo")
        # force sync for demo records
        cls.env["endpoint.endpoint"].search([])._handle_registry_sync()

    def tearDown(self):
        # Clear cache for method ``ir.http.routing_map()``
        self.env.registry.clear_cache("routing")
        super().tearDown()

    def _make_url(self, route):
        return f"http://127.0.0.1:{tools.config['http_port']}{route}"

    def _make_request(self, route, api_key=None, headers=None):
        # use requests because you cannot easily manipulate the request w/ `url_open`
        headers = headers or {}
        if api_key:
            headers.update({"Authorization": f"bearer {api_key}"})
        return requests.get(self._make_url(route), headers=headers, timeout=60)

    @mute_logger("odoo.addons.endpoint_auth_bearer")
    def test_call_no_key(self):
        route = "/demo/api/key"
        response = self._make_request(route)
        self.assertEqual(response.status_code, 401)

    def test_call_good_key(self):
        route = "/demo/api/key"
        expiration_date = datetime.datetime.today() + datetime.timedelta(days=1)
        key = (
            self.env["res.users.apikeys"]
            .with_user(self.user)
            ._generate(None, "Test api key", expiration_date)
        )
        self.user.api_key_ids.flush_model()
        response = self._make_request(route, api_key=key)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")

    @mute_logger("endpoint.endpoint")
    def test_call_bad_key(self):
        route = "/demo/api/key"
        response = self._make_request(route, api_key="bad_key")
        self.assertEqual(response.status_code, 401)
