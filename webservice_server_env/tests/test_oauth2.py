# Copyright 2023 Camptocamp SA
# @author Alexandre Fayolle <alexandre.fayolle@camptocamp.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import os
from unittest import mock

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
