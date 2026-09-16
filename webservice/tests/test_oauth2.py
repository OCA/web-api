# Copyright 2023 Camptocamp SA
# @author Alexandre Fayolle <alexandre.fayolle@camptocamp.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import base64
import json
import time
from urllib.parse import quote

import responses
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError

from odoo import exceptions

from .common import CommonWebService, mock_cursor


class TestWebServiceOauth2BackendApplication(CommonWebService):
    @classmethod
    def _setup_records(cls):
        res = super()._setup_records()
        cls.url = "https://localhost.demo.odoo/"
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
        now = time.time()
        duration = 3600
        responses.add(
            responses.POST,
            f"{self.url}oauth2/token",
            json={
                "access_token": "cool_token",
                "token_type": "Bearer",
                "expires_in": duration,
                "expires_at": now + duration,
            },
        )
        responses.add(responses.GET, f"{self.url}endpoint", body="OK")
        with mock_cursor(self.env.cr):
            result = self.webservice.call("get", url=f"{self.url}endpoint")
        self.webservice.invalidate_recordset()
        self.assertEqual(len(responses.calls), 2)
        call_token = json.loads(responses.calls[0].response.content.decode())
        webs_token = json.loads(self.webservice.oauth2_token)
        self.assertEqual(call_token["access_token"], webs_token["access_token"])
        self.assertEqual(call_token["token_type"], webs_token["token_type"])
        self.assertEqual(call_token["expires_in"], webs_token["expires_in"])
        self.assertAlmostEqual(
            call_token["expires_at"],
            webs_token["expires_at"],
            delta=1,  # Accept a diff of 1s
        )
        self.assertEqual(responses.calls[1].response.content.decode(), "OK")
        self.assertEqual(result.decode(), "OK")

    @responses.activate
    def test_update_token(self):
        now = time.time()
        duration = 3600
        responses.add(
            responses.POST,
            f"{self.url}oauth2/token",
            json={
                "access_token": "cool_token",
                "expires_at": now + duration,
                "expires_in": duration,
                "token_type": "Bearer",
            },
        )
        responses.add(responses.GET, f"{self.url}endpoint", body="OK")
        self.webservice.oauth2_token = json.dumps(
            {
                "access_token": "old_token",
                "expires_at": now + 10,  # in the near future
                "expires_in": duration,
                "token_type": "Bearer",
            }
        )
        self.webservice.flush_model()
        with mock_cursor(self.env.cr):
            result = self.webservice.call("get", url=f"{self.url}endpoint")
            self.env.cr.commit.assert_called_once_with()  # one call with no args
        self.webservice.invalidate_recordset()
        self.assertEqual(len(responses.calls), 2)
        call_token = json.loads(responses.calls[0].response.content.decode())
        webs_token = json.loads(self.webservice.oauth2_token)
        self.assertEqual(call_token["access_token"], webs_token["access_token"])
        self.assertEqual(call_token["token_type"], webs_token["token_type"])
        self.assertEqual(call_token["expires_in"], webs_token["expires_in"])
        self.assertAlmostEqual(
            call_token["expires_at"],
            webs_token["expires_at"],
            delta=1,  # Accept a diff of 1s
        )
        self.assertEqual(responses.calls[1].response.content.decode(), "OK")
        self.assertEqual(result.decode(), "OK")

    @responses.activate
    def test_update_token_with_error(self):
        now = time.time()
        duration = 3600
        responses.add(
            responses.POST,
            f"{self.url}oauth2/token",
            json={"error": "invalid_grant", "error_description": "invalid grant"},
            status=404,
        )
        responses.add(responses.GET, f"{self.url}endpoint", body="NOK", status=403)
        self.webservice.oauth2_token = json.dumps(
            {
                "access_token": "old_token",
                "expires_at": now + 10,  # in the near future
                "expires_in": duration,
                "token_type": "Bearer",
            }
        )
        self.webservice.flush_model()
        with mock_cursor(self.env.cr):
            with self.assertRaises(InvalidGrantError):
                self.webservice.call("get", url=f"{self.url}endpoint")
            self.env.cr.commit.assert_not_called()
            self.env.cr.close.assert_called_once_with()  # one call with no args
        self.webservice.invalidate_recordset()
        self.assertEqual(len(responses.calls), 1)  # ``GET`` is not executed
        self.assertEqual(responses.calls[0].request.method, "POST")
        self.assertEqual(
            json.loads(responses.calls[0].response.content.decode()),
            {"error": "invalid_grant", "error_description": "invalid grant"},
        )
        self.assertEqual(
            json.loads(self.webservice.oauth2_token)["access_token"],
            "old_token",
        )

    @responses.activate
    def test_call_with_content_only_false_returns_response(self):
        now = time.time()
        duration = 3600
        responses.add(
            responses.POST,
            f"{self.url}oauth2/token",
            json={
                "access_token": "cool_token",
                "token_type": "Bearer",
                "expires_in": duration,
                "expires_at": now + duration,
            },
        )
        responses.add(responses.POST, f"{self.url}endpoint", json={"ok": True})

        with mock_cursor(self.env.cr):
            response = self.webservice.call(
                "post",
                url=f"{self.url}endpoint",
                data="payload",
                content_only=False,
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})

    @responses.activate
    def test_fetch_token_client_secret_basic(self):
        """Client credentials are sent as an HTTP Basic Authorization header.

        Scenario:
            1. Fetch a token with the default (HTTP Basic) authentication.
        Expected:
            - The token request carries a Basic Authorization header built from
              the client id and secret.
            - The client secret is not duplicated in the request body.
        """
        self.webservice.oauth2_client_auth_method = "client_secret_basic"
        now = time.time()
        duration = 3600
        responses.add(
            responses.POST,
            f"{self.url}oauth2/token",
            json={
                "access_token": "cool_token",
                "token_type": "Bearer",
                "expires_in": duration,
                "expires_at": now + duration,
            },
        )
        responses.add(responses.GET, f"{self.url}endpoint", body="OK")
        with mock_cursor(self.env.cr):
            self.webservice.call("get", url=f"{self.url}endpoint")
        token_request = responses.calls[0].request
        expected = base64.b64encode(b"some_client_id:shh_secret").decode()
        self.assertEqual(token_request.headers["Authorization"], f"Basic {expected}")
        self.assertNotIn("client_secret", token_request.body or "")

    @responses.activate
    def test_fetch_token_custom_header_get(self):
        """Client credentials are sent verbatim in a custom header over GET.

        Scenario:
            1. Configure the backend to authenticate with a custom Authorization
               header and to request the token with a GET.
            2. Trigger a call so a new token is fetched.
        Expected:
            - The token request uses the GET method.
            - It carries the configured custom Authorization header, unaltered.
        """
        self.webservice.write(
            {
                "oauth2_client_auth_method": "custom_header",
                "oauth2_token_method": "get",
                "oauth2_client_auth_header": "Authorization",
                "oauth2_client_auth_value": "SSWS some_static_token",
            }
        )
        now = time.time()
        duration = 3600
        responses.add(
            responses.GET,
            f"{self.url}oauth2/token",
            json={
                "access_token": "cool_token",
                "token_type": "Bearer",
                "expires_in": duration,
                "expires_at": now + duration,
            },
        )
        responses.add(responses.GET, f"{self.url}endpoint", body="OK")
        with mock_cursor(self.env.cr):
            self.webservice.call("get", url=f"{self.url}endpoint")
        token_request = responses.calls[0].request
        self.assertEqual(token_request.method, "GET")
        self.assertEqual(
            token_request.headers["Authorization"], "SSWS some_static_token"
        )

    def test_client_secret_basic_auth_validation(self):
        """HTTP Basic auth requires the client id and secret.

        Scenario:
            1. Create an OAuth2 backend with the HTTP Basic authentication but
               without a client id and secret.
        Expected:
            - Validation fails asking for the client id and secret.
        """
        msg = (
            r"requires 'OAuth2' authentication. However, the following "
            r"field\(s\) are not valued: Client ID, Client Secret"
        )
        with self.assertRaisesRegex(exceptions.UserError, msg):
            self.env["webservice.backend"].create(
                {
                    "name": "WebService OAuth2 basic missing creds",
                    "tech_name": "test_oauth2_basic_missing",
                    "auth_type": "oauth2",
                    "protocol": "http",
                    "url": self.url,
                    "oauth2_flow": "backend_application",
                    "oauth2_client_auth_method": "client_secret_basic",
                    "oauth2_token_url": f"{self.url}oauth2/token",
                }
            )

    def test_custom_header_auth_validation(self):
        """Custom-header auth requires the header value, not the client id/secret.

        Scenario:
            1. Create an OAuth2 backend with the custom Authorization header
               method, without a client id/secret and without a header value.
        Expected:
            - Validation fails asking only for the header value; the client id
              and secret are not reported as missing.
        """
        msg = (
            r"requires 'OAuth2' authentication. However, the following "
            r"field\(s\) are not valued: Client Auth Header Value"
        )
        with self.assertRaisesRegex(exceptions.UserError, msg):
            self.env["webservice.backend"].create(
                {
                    "name": "WebService OAuth2 custom header missing value",
                    "tech_name": "test_oauth2_customhdr_missing",
                    "auth_type": "oauth2",
                    "protocol": "http",
                    "url": self.url,
                    "oauth2_flow": "backend_application",
                    "oauth2_client_auth_method": "custom_header",
                    "oauth2_client_auth_header": "Authorization",
                    "oauth2_token_url": f"{self.url}oauth2/token",
                }
            )


class TestWebServiceOauth2WebApplication(CommonWebService):
    @classmethod
    def _setup_records(cls):
        res = super()._setup_records()
        cls.url = "https://localhost.demo.odoo/"
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
                "oauth2_authorization_url": f"{cls.url}authorize",
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
            "url": "https://localhost.demo.odoo/authorize?response_type=code&"
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
        now = time.time()
        duration = 3600
        expires_timestamp = now + duration
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
        adapter = self.webservice._get_adapter()
        token = adapter._fetch_token_from_authorization("some code")
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(
            "cool_token",
            json.loads(responses.calls[0].response.content.decode())["access_token"],
        )
        self.assertEqual("cool_token", token["access_token"])


class TestWebServiceOauth2FlowReset(CommonWebService):
    """``oauth2_flow`` must be reset on any write, not only via the UI.

    This is a plain ORM-level guarantee independent of ``server_environment``
    (see ``webservice_server_env`` for the extra guarantee that applies when
    that module is installed).
    """

    @classmethod
    def _setup_records(cls):
        res = super()._setup_records()
        cls.url = "https://localhost.demo.odoo/"
        cls.webservice = cls.env["webservice.backend"].create(
            {
                "name": "WebService OAuth2",
                "tech_name": "test_oauth2_reset",
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

    def test_write_resets_oauth2_flow_when_auth_type_changes(self):
        self.webservice.write({"auth_type": "none"})
        self.assertFalse(self.webservice.oauth2_flow)

    def test_write_keeps_oauth2_flow_when_auth_type_stays_oauth2(self):
        self.webservice.write({"oauth2_client_secret": "new_secret"})
        self.assertEqual(self.webservice.oauth2_flow, "backend_application")

    def test_create_resets_oauth2_flow_for_non_oauth2_auth_type(self):
        ws = self.env["webservice.backend"].create(
            {
                "name": "WebService No Auth",
                "tech_name": "test_oauth2_reset_create",
                "auth_type": "none",
                "protocol": "http",
                "url": self.url,
                # Inconsistent on purpose: no `create`/`write` should ever
                # leave this set together with a non-oauth2 `auth_type`.
                "oauth2_flow": "backend_application",
            }
        )
        self.assertFalse(ws.oauth2_flow)

    def test_onchange_resets_oauth2_flow(self):
        ws = self.webservice.new(
            {"auth_type": "oauth2", "oauth2_flow": "backend_application"}
        )
        ws.auth_type = "none"
        ws._onchange_auth_type()
        self.assertFalse(ws.oauth2_flow)
