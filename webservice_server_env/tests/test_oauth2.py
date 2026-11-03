# Copyright 2023 Camptocamp SA
# @author Alexandre Fayolle <alexandre.fayolle@camptocamp.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import os
from unittest import mock

from odoo.tests import Form

from odoo.addons.server_environment import server_env
from odoo.addons.server_environment.models import server_env_mixin
from odoo.addons.webservice.tests.common import CommonWebService


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

    def test_oauth2_flow_compute_with_server_env(self):
        """Check the ``compute`` method when updating server envs"""
        ws = self.webservice
        url = self.url
        for auth_type, oauth2_flow in [
            (tp, fl)
            for tp in ws._fields["auth_type"].get_values(ws.env)
            for fl in ws._fields["oauth2_flow"].get_values(ws.env)
        ]:
            # Update env with current ``auth_type`` and ``oauth2_flow``
            with mock.patch.dict(
                os.environ,
                {
                    "SERVER_ENV_CONFIG": f"""
[webservice_backend.test_oauth2_web]
auth_type = {auth_type}
oauth2_flow = {oauth2_flow}
oauth2_clientid = some_client_id
oauth2_client_secret = shh_secret
oauth2_token_url = {url}oauth2/token
oauth2_audience = {url}
oauth2_authorization_url = {url}/authorize
""",
                },
            ):
                server_env_mixin.serv_config = server_env._load_config()  # Reload vars
                ws.invalidate_recordset()  # Avoid reading from cache
                if auth_type == "oauth2":
                    self.assertEqual(ws.oauth2_flow, oauth2_flow)
                else:
                    self.assertFalse(ws.oauth2_flow)

    def test_oauth2_flow_compute_with_ui(self):
        """Check the ``compute`` method when updating WS from UI"""
        ws = self.webservice
        url = self.url
        form_xmlid = "webservice.webservice_backend_form_view"
        for auth_type, oauth2_flow in [
            (tp, fl)
            for tp in ws._fields["auth_type"].get_values(ws.env)
            for fl in ws._fields["oauth2_flow"].get_values(ws.env)
        ]:
            next_ws_id = ws.sudo().search([], order="id desc", limit=1).id + 1
            # Create a new WS with each ``auth_type/oauth2_flow`` couple through UI
            with Form(ws.browse(), form_xmlid) as ws_form:
                # Common fields
                ws_form.name = "WebService Test UI"
                ws_form.tech_name = f"webservice_test_ui_{next_ws_id}"
                ws_form.protocol = "http"
                ws_form.url = url
                ws_form.content_type = "application/xml"
                ws_form.auth_type = auth_type
                # Auth type specific fields
                if auth_type == "api_key":
                    ws_form.api_key = "Test Api Key"
                    ws_form.api_key_header = "Test Api Key Header"
                if auth_type == "oauth2":
                    ws_form.oauth2_flow = oauth2_flow
                    # ``oauth2_client_auth_method`` is only shown (and drives the
                    # visibility of the client id/secret) for the backend flow.
                    if oauth2_flow == "backend_application":
                        ws_form.oauth2_client_auth_method = "client_secret_basic"
                    ws_form.oauth2_clientid = "Test Client ID"
                    ws_form.oauth2_client_secret = "Test Client Secret"
                    ws_form.oauth2_token_url = f"{url}oauth2/token"
                    if oauth2_flow == "web_application":
                        ws_form.oauth2_scope = "Test Scope"
                        ws_form.oauth2_authorization_url = f"{url}oauth2/auth"
                if auth_type == "user_pwd":
                    ws_form.username = "Test Username"
                    ws_form.password = "Test Password"
            ws = ws_form.save()
            # Check that ``oauth2_flow`` is the expected one after creation only if the
            # ``auth_type`` is "oauth2", else it should be False
            self.assertEqual(
                ws.oauth2_flow, oauth2_flow if ws.auth_type == "oauth2" else False
            )
            # Change WS's ``auth_type`` through UI
            with Form(ws, form_xmlid) as ws_form:
                new_auth_type = "none" if ws.auth_type == "oauth2" else "oauth2"
                ws_form.auth_type = new_auth_type
                if new_auth_type == "oauth2":
                    ws_form.oauth2_flow = oauth2_flow
                    if oauth2_flow == "backend_application":
                        ws_form.oauth2_client_auth_method = "client_secret_basic"
                    ws_form.oauth2_clientid = "Test Client ID"
                    ws_form.oauth2_client_secret = "Test Client Secret"
                    ws_form.oauth2_token_url = f"{url}oauth2/token"
                    if oauth2_flow == "web_application":
                        ws_form.oauth2_scope = "Test Scope"
                        ws_form.oauth2_authorization_url = f"{url}oauth2/auth"
            ws = ws_form.save()
            # Check that ``oauth2_flow`` is the expected one after update only if the
            # ``auth_type`` is "oauth2", else it should be False
            self.assertEqual(
                ws.oauth2_flow, oauth2_flow if ws.auth_type == "oauth2" else False
            )
