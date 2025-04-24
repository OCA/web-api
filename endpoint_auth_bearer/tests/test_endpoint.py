# Copyright 2025 feihu.zhang
# @author: feihu.zhang <feihu.zhang@live.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).


import datetime

import werkzeug

from odoo.exceptions import AccessDenied
from odoo.tools.misc import mute_logger

from odoo.addons.endpoint.tests.common import CommonEndpoint


class TestEndpoint(CommonEndpoint):
    @classmethod
    def _setup_records(cls):
        super()._setup_records()
        cls.user = cls.env.ref("base.user_demo")
        cls.endpoint = cls.env.ref("endpoint_auth_bearer.endpoint_demo_1")
        cls.env = cls.env(user=cls.user)
        return

    @mute_logger("endpoint.endpoint")
    def test_endpoint_validate_request_no_key(self):
        endpoint = self.endpoint.copy(
            {
                "route": "/api-key-test",
                "request_method": "GET",
            }
        )
        with self.assertRaises(AccessDenied):
            with self._get_mocked_request(
                httprequest={"method": "GET"},
            ) as req:
                endpoint._validate_request(req)

    @mute_logger("endpoint.endpoint")
    def test_endpoint_validate_request_bad_key(self):
        endpoint = self.endpoint.copy(
            {
                "route": "/api-key-test",
                "request_method": "GET",
            }
        )
        with self.assertRaises(werkzeug.exceptions.Unauthorized):
            with self._get_mocked_request(
                httprequest={"method": "GET"},
                extra_headers={"Authorization": "Bearer bad_key"},
            ) as req:
                endpoint._validate_request(req)

    def test_endpoint_validate_request_good_key(self):
        endpoint = self.endpoint.copy(
            {
                "route": "/api-key-test",
                "request_method": "GET",
            }
        )
        expiration_date = datetime.datetime.today() + datetime.timedelta(days=1)
        key = (
            self.env["res.users.apikeys"]
            .with_user(self.user)
            ._generate(None, "Test api key", expiration_date)
        )
        self.user.api_key_ids.flush_model()
        with self._get_mocked_request(
            httprequest={"method": "GET"},
            extra_headers={"Authorization": f"Bearer {key}"},
        ) as req:
            endpoint._validate_request(req)
