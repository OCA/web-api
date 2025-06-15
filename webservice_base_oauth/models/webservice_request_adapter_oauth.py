# Copyright 2020 Creu Blanca
# Copyright 2022 Camptocamp SA
# @author Simone Orsi <simahawk@gmail.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import json
import time

from oauthlib.oauth2 import BackendApplicationClient, WebApplicationClient
from requests_oauthlib import OAuth2Session

from odoo import models


class WebserviceRequestAdapter(models.AbstractModel):
    _inherit = "webservice.request.adapter"

    def _get_client(self, oauth_params: dict):
        if self.oauth2_flow == "web_application":
            return WebApplicationClient(
                client_id=oauth_params["oauth2_clientid"],
                code=oauth_params.get("oauth2_autorization"),
                redirect_uri=oauth_params["redirect_url"],
            )
        return BackendApplicationClient(client_id=oauth_params["oauth2_clientid"])

    # OAuth BackendApplicationClient

    def _request_do(self, method, url=None, **kwargs):
        if self.auth_type != "oauth2":
            timeout = (self.connect_timeout, self.read_timeout)
            client = BackendApplicationClient(client_id=self.oauth2_clientid)
            with OAuth2Session(client=client, token=self.token) as session:
                response = session.request(method, url, timeout=timeout, **kwargs)
                response.raise_for_status()
                return response
        return super()._request(method, url, **kwargs)

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        # cached value to avoid hitting the database each time we need the token
        self._token = {}

    def _is_token_valid(self, token):
        """Validate given oauth2 token.

        We consider that a token in valid if it has at least 10% left of
        its valid duration. So if a token has a validity of 1h, we will
        renew it if we try to use it 6 minutes before its expiration date.
        """
        expires_at = token.get("expires_at", 0)
        expires_in = token.get("expires_in", 3600)  # default to 1h
        now = time.time()
        return now <= (expires_at - 0.1 * expires_in)

    @property
    def token(self):
        """Return a valid oauth2 token.

        The tokens are stored in the database, and we check if they are still
        valid, and renew them if needed.
        """
        if self._is_token_valid(self._token):
            return self._token
        backend = self
        with backend.env.registry.cursor() as cr:
            cr.execute(
                "SELECT oauth2_token FROM webservice_backend "
                "WHERE id=%s "
                "FOR NO KEY UPDATE",  # prevent concurrent token fetching
                (backend.id,),
            )
            token_str = cr.fetchone()[0] or "{}"
            token = json.loads(token_str)
            if self._is_token_valid(token):
                self._token = token
            else:
                new_token = self._fetch_new_token(old_token=token)
                cr.execute(
                    "UPDATE webservice_backend " "SET oauth2_token=%s " "WHERE id=%s",
                    (json.dumps(new_token), backend.id),
                )
                self._token = new_token
        return self._token

    def _fetch_new_token(self, old_token):
        # TODO: check if the old token has a refresh_token that can
        # be used (and use it in that case)
        oauth_params = self.sudo().read(
            [
                "oauth2_clientid",
                "oauth2_client_secret",
                "oauth2_token_url",
                "oauth2_audience",
                "redirect_url",
            ]
        )[0]
        client = self._get_client(oauth_params)
        with OAuth2Session(client=client) as session:
            token = session.fetch_token(
                token_url=oauth_params["oauth2_token_url"],
                cliend_id=oauth_params["oauth2_clientid"],
                client_secret=oauth_params["oauth2_client_secret"],
                audience=oauth_params.get("oauth2_audience") or "",
            )
        return token

    # OAuth WebApplicationClient

    def fetch_token_from_authorization(self, authorization_code):
        oauth_params = self.sudo().read(
            [
                "oauth2_clientid",
                "oauth2_client_secret",
                "oauth2_token_url",
                "oauth2_audience",
                "redirect_url",
            ]
        )[0]
        client = WebApplicationClient(client_id=oauth_params["oauth2_clientid"])
        with OAuth2Session(
            client=client, redirect_uri=oauth_params.get("redirect_url")
        ) as session:
            token = session.fetch_token(
                oauth_params["oauth2_token_url"],
                client_secret=oauth_params["oauth2_client_secret"],
                code=authorization_code,
                audience=oauth_params.get("oauth2_audience") or "",
                include_client_id=True,
            )
        return token

    def redirect_to_authorize(self, **authorization_url_extra_params):
        """set the oauth2_state on the backend
        :return: the webservice authorization url with the proper parameters
        """
        # we are normally authenticated at this stage, so no need to sudo()
        backend = self
        oauth_params = backend.read(
            [
                "oauth2_clientid",
                "oauth2_token_url",
                "oauth2_audience",
                "oauth2_authorization_url",
                "oauth2_scope",
                "redirect_url",
            ]
        )[0]
        client = WebApplicationClient(
            client_id=oauth_params["oauth2_clientid"],
        )

        with OAuth2Session(
            client=client,
            redirect_uri=oauth_params.get("redirect_url"),
        ) as session:
            authorization_url, state = session.authorization_url(
                backend.oauth2_authorization_url, **authorization_url_extra_params
            )
            backend.oauth2_state = state
            return authorization_url
