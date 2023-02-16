# Copyright 2021 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import os
import unittest

import requests

from odoo import tools
from odoo.tests.common import HttpSavepointCase
from odoo.tools.misc import mute_logger


@unittest.skipIf(os.getenv("SKIP_HTTP_CASE"), "EndpoinAuthApikeytHttpCase skipped")
class EndpoinAuthApikeytHttpCase(HttpSavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api_key = cls.env.ref("endpoint_auth_api_key.auth_api_key_demo")
        cls.api_key2 = cls.env.ref("endpoint_auth_api_key.auth_api_key_demo2")
        # force sync for demo records
        cls.env["endpoint.endpoint"].search([])._handle_registry_sync()

    def tearDown(self):
        self.env["ir.http"]._clear_routing_map()
        super().tearDown()

    def _make_url(self, route):
        return "http://127.0.0.1:%s%s" % (tools.config["http_port"], route)

    def _make_request(self, route, api_key=None, headers=None):
        # use requests because you cannot easily manipulate the request w/ `url_open`
        headers = headers or {}
        if api_key:
            headers.update({"API-KEY": api_key.key})
        return requests.get(self._make_url(route), headers=headers)

    @mute_logger("odoo.addons.auth_api_key.models.ir_http")
    def test_call_no_key(self):
        route = "/demo/api/key"
        response = self._make_request(route)
        self.assertEqual(response.status_code, 403)

    def test_call_good_key(self):
        route = "/demo/api/key"
        response = self._make_request(route, api_key=self.api_key)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")

    @mute_logger("endpoint.endpoint")
    def test_call_bad_key(self):
        route = "/demo/api/key"
        response = self._make_request(route, api_key=self.api_key2)
        self.assertEqual(response.status_code, 403)
