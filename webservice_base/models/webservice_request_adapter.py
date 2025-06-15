# Copyright 2020 Creu Blanca
# Copyright 2022 Camptocamp SA
# @author Simone Orsi <simahawk@gmail.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import logging

import requests

from odoo import models

from ..utils import sanitize_url_for_log

_logger = logging.getLogger(__name__)


class WebserviceRequestAdapter(models.AbstractModel):
    _name = "webservice.request.adapter"
    _description = "Webservice Requests Adapter"

    # PUBLIC API

    def get(self, **kwargs):
        return self._request("get", **kwargs)

    def post(self, **kwargs):
        return self._request("post", **kwargs)

    def put(self, **kwargs):
        return self._request("put", **kwargs)

    # PRIVATE IMPLEMENTATION

    def _request(self, method, url=None, url_params=None, **kwargs):
        content_only = kwargs.pop("content_only", True)
        url, req_kwargs = self._prepare_request(url, url_params, **kwargs)
        _logger.debug("%s call to %s", method, sanitize_url_for_log(url))
        response = self._request_do(method, url, **req_kwargs)
        response.raise_for_status()
        if content_only:
            return response.content
        return response

    def _prepare_request(self, url=None, url_params=None, **kwargs):
        url = self._get_url(url=url, url_params=url_params)
        req_kwargs = kwargs.copy()
        req_kwargs.update(
            {
                "auth": self._get_auth(**kwargs),
                "headers": self._get_headers(**kwargs),
            }
        )
        return url, req_kwargs

    def _request_do(self, method, url=None, **kwargs):
        timeout = kwargs.pop(
            "timeout",
            (
                self.connect_timeout,
                self.read_timeout,
            ),
        )
        return requests.request(method, url, timeout=timeout, **kwargs)

    def _get_url(self, url=None, url_params=None, **kwargs):
        url = url or self.get("url")
        url_params = url_params or kwargs
        return url.format(**url_params)

    def _get_auth(self, auth=False, **kwargs):
        if auth:
            return auth
        if self.auth_type == "user_pwd" and self.username and self.password:
            return self.username, self.password
        return None

    def _get_headers(self, content_type=False, headers=False, **kwargs):
        headers = headers or {}
        if content_type or self.content_type:
            headers["Content-Type"] = content_type or self.content_type
        if self.auth_type == "api_key":
            headers[self.api_key_header] = self.api_key
        return headers
