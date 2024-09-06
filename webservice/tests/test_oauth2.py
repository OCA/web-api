# Copyright 2023 Camptocamp SA
# @author Alexandre Fayolle <alexandre.fayolle@camptocamp.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import json
import os
import time
from urllib.parse import quote

import responses
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError

from odoo.addons.server_environment import server_env
from odoo.addons.server_environment.models import server_env_mixin

from .common import CommonWebService, mock_cursor


class TestWebServiceOauth2BackendApplication(CommonWebService):
    @classmethod
    def _setup_records(cls):

        res = super()._setup_records()
        cls.url = "https://localhost.demo.odoo/"
        os.environ["SERVER_ENV_CONFIG"] = "\n".join(
            [
                "[webservice_backend.test_oauth2_back]",
                "auth_type = oauth2",
                "oauth2_flow = backend_application",
                "oauth2_clientid = some_client_id",
                "oauth2_client_secret = shh_secret",
                f"oauth2_token_url = {cls.url}oauth2/token",
                f"oauth2_audience = {cls.url}",
            ]
        )
        cls.webservice = cls.env["webservice.backend"].create(
            {
                "name": "WebService OAuth2",
                "tech_name": "test_oauth2_back",
                "auth_type": "oauth2",
                "protocol": "http",
                "url": cls.url,
                "oauth2_flow": "backend_application",
                "content_type": "application/xml",
                "oauth2_clientid": "some_client_id",
                "oauth2_client_secret": "shh_secret",
                "oauth2_token_url": f"{cls.url}oauth2/token",
                "oauth2_audience": cls.url,
            }
        )
        return res

    def test_get_adapter_protocol(self):
        protocol = self.webservice._get_adapter_protocol()
        self.assertEqual(protocol, "http+oauth2-backend_application")

    @responses.activate
    def test_fetch_token(self):
        duration = 3600
        expires_timestamp = time.time() + duration
        responses.add(
            responses.POST,
            f"{self.url}oauth2/token",
            json={
                "access_token": "cool_token",
                "expires_at": expires_timestamp,
                "expires_in": duration,
                "token_type": "Bearer",
            },
        )
        responses.add(responses.GET, f"{self.url}endpoint", body="OK")

        with mock_cursor(self.env.cr):
            result = self.webservice.call("get", url=f"{self.url}endpoint")
        self.webservice.invalidate_recordset()
        self.assertTrue("cool_token" in self.webservice.oauth2_token)
        self.assertEqual(result, b"OK")

    @responses.activate
    def test_update_token(self):
        duration = 3600
        self.webservice.oauth2_token = json.dumps(
            {
                "access_token": "old_token",
                "expires_at": time.time() + 10,  # in the near future
                "expires_in": duration,
                "token_type": "Bearer",
            }
        )
        self.webservice.flush_model()

        expires_timestamp = time.time() + duration
        responses.add(
            responses.POST,
            f"{self.url}oauth2/token",
            json={
                "access_token": "cool_token",
                "expires_at": expires_timestamp,
                "expires_in": duration,
                "token_type": "Bearer",
            },
        )
        responses.add(responses.GET, f"{self.url}endpoint", body="OK")

        with mock_cursor(self.env.cr):
            result = self.webservice.call("get", url=f"{self.url}endpoint")
            self.env.cr.commit.assert_called_once_with()  # one call with no args

        self.webservice.invalidate_recordset()
        self.assertTrue("cool_token" in self.webservice.oauth2_token)
        self.assertEqual(result, b"OK")

    @responses.activate
    def test_update_token_with_error(self):
        duration = 3600
        self.webservice.oauth2_token = json.dumps(
            {
                "access_token": "old_token",
                "expires_at": time.time() + 10,  # in the near future
                "expires_in": duration,
                "token_type": "Bearer",
            }
        )
        self.webservice.flush_model()

        responses.add(
            responses.POST,
            f"{self.url}oauth2/token",
            json={
                "error": "invalid_grant",
                "error_description": "invalid grant",
            },
            status=404,
        )
        responses.add(responses.GET, f"{self.url}endpoint", body="NOK", status=403)

        with mock_cursor(self.env.cr):
            with self.assertRaises(InvalidGrantError):
                self.webservice.call("get", url=f"{self.url}endpoint")
            self.env.cr.commit.assert_not_called()
            self.env.cr.close.assert_called_once_with()  # one call with no args

        self.webservice.invalidate_recordset()
        self.assertTrue("old_token" in self.webservice.oauth2_token)


class TestWebServiceOauth2WebApplication(CommonWebService):
    @classmethod
    def _setup_records(cls):
        res = super()._setup_records()
        cls.url = "https://localhost.demo.odoo/"
        os.environ["SERVER_ENV_CONFIG"] = "\n".join(
            [
                "[webservice_backend.test_oauth2_web]",
                "auth_type = oauth2",
                "oauth2_flow = web_application",
                "oauth2_clientid = some_client_id",
                "oauth2_client_secret = shh_secret",
                f"oauth2_token_url = {cls.url}oauth2/token",
                f"oauth2_audience = {cls.url}",
                f"oauth2_authorization_url = {cls.url}/authorize",
            ]
        )
        cls.webservice = cls.env["webservice.backend"].create(
            {
                "name": "WebService OAuth2",
                "tech_name": "test_oauth2_web",
                "auth_type": "oauth2",
                "protocol": "http",
                "url": cls.url,
                "oauth2_flow": "web_application",
                "content_type": "application/xml",
                "oauth2_clientid": "some_client_id",
                "oauth2_client_secret": "shh_secret",
                "oauth2_token_url": f"{cls.url}oauth2/token",
                "oauth2_audience": cls.url,
                "oauth2_authorization_url": f"{cls.url}/authorize",
            }
        )
        return res

    def test_get_adapter_protocol(self):
        protocol = self.webservice._get_adapter_protocol()
        self.assertEqual(protocol, "http+oauth2-web_application")

    def test_authorization_code(self):
        action = self.webservice.button_authorize()
        expected_action = {
            "type": "ir.actions.act_url",
            "target": "self",
            "url": "https://localhost.demo.odoo//authorize?response_type=code&"
            "client_id=some_client_id&"
            f"redirect_uri={quote(self.webservice.redirect_url, safe='')}&state=",
        }
        self.assertEqual(action["type"], expected_action["type"])
        self.assertEqual(action["target"], expected_action["target"])
        self.assertTrue(
            action["url"].startswith(expected_action["url"]),
            f"Got url:\n{action['url']}\nexpected:\n{expected_action['url']}",
        )

    @responses.activate
    def test_fetch_token_from_auth(self):
        duration = 3600
        expires_timestamp = time.time() + duration
        responses.add(
            responses.POST,
            self.webservice.oauth2_token_url,
            json={
                "access_token": "cool_token",
                "expires_at": expires_timestamp,
                "expires_in": duration,
                "token_type": "Bearer",
            },
        )
        code = "some code"
        adapter = self.webservice._get_adapter()
        token = adapter._fetch_token_from_authorization(code)
        self.assertEqual("cool_token", token["access_token"])

    def test_oauth2_flow_compute(self):
        # Test with current configuration
        env = os.environ
        self.assertIn("auth_type = oauth2\n", env["SERVER_ENV_CONFIG"])
        self.assertIn("oauth2_flow = web_application\n", env["SERVER_ENV_CONFIG"])
        server_env_mixin.serv_config = server_env._load_config()  # Reload env vars
        self.webservice.invalidate_recordset()  # Force recomputation when reading
        self.assertEqual(self.webservice.oauth2_flow, "web_application")

        # Update configuration: ``auth_type`` is changed to ``none``
        env["SERVER_ENV_CONFIG"] = env["SERVER_ENV_CONFIG"].replace(
            "auth_type = oauth2", "auth_type = none"
        )
        server_env_mixin.serv_config = server_env._load_config()  # Reload env vars
        self.webservice.invalidate_recordset()  # Clear cache => read forces compute
        self.assertFalse(self.webservice.oauth2_flow)

        # Update configuration: ``auth_type`` is reverted to ``oauth2``,
        # and ``oauth2_flow`` is updated to ``backend_application``
        env["SERVER_ENV_CONFIG"] = (
            env["SERVER_ENV_CONFIG"]
            .replace("auth_type = none", "auth_type = oauth2")
            .replace(
                "oauth2_flow = web_application", "oauth2_flow = backend_application"
            )
        )
        server_env_mixin.serv_config = server_env._load_config()  # Reload env vars
        self.webservice.invalidate_recordset()  # Clear cache => read forces compute
        self.assertEqual(self.webservice.oauth2_flow, "backend_application")
