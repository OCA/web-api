# Copyright 2020 Creu Blanca
# Copyright 2022 Camptocamp SA
# @author Simone Orsi <simahawk@gmail.com>
# @author Alexandre Fayolle <alexandre.fayolle@camptocamp.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging

import requests

from odoo import Command, api, exceptions, fields, models

from ..utils import sanitize_url_for_log

_logger = logging.getLogger(__name__)


class WebserviceRequestMixin(models.AbstractModel):
    """Auth configuration + HTTP call features for any webservice-like record.

    Any model inheriting this mixin becomes able to issue authenticated HTTP
    requests based on its own ``auth_type``/credential fields, resolved via
    ``self._get_base_url()`` which must be implemented by the model.

    ``call()`` dispatches by ``self._get_protocol()`` (``self.protocol`` by
    default) to a ``_handle_call_for_<protocol>`` method that actually
    performs the request - ``_handle_call_for_http`` today. A new protocol is
    added by implementing a new ``_handle_call_for_<protocol>``.

    Extra auth types are added by other modules via plain model inheritance:
    add the new value to the ``auth_type`` selection, add fields tagged with
    the matching ``auth_type=<value>`` parameter, and implement
    ``_get_auth_for_<value>``/``_get_headers_for_<value>`` and/or override
    ``_request`` when the whole HTTP request flow needs to change (e.g.
    oauth2).

    """

    _name = "webservice.request.mixin"
    _description = "Webservice Request Mixin"

    tech_name = fields.Char(
        required=True,
        copy=False,
        help="Unique name for technical purposes. "
        "Automatically generated from the name if left empty.",
    )
    protocol = fields.Selection([("http", "HTTP Request")], required=True)
    auth_type = fields.Selection(
        selection=[
            ("none", "Public"),
            ("user_pwd", "Username & password"),
            ("api_key", "API Key"),
        ],
        required=True,
    )
    username = fields.Char(auth_type="user_pwd")
    password = fields.Char(auth_type="user_pwd")
    api_key = fields.Char(string="API Key", auth_type="api_key")
    api_key_header = fields.Char(string="API Key header", auth_type="api_key")
    content_type = fields.Selection(
        [
            ("application/json", "JSON"),
            ("application/xml", "XML"),
            ("application/x-www-form-urlencoded", "Form"),
        ],
    )
    timeout = fields.Float(
        help="Timeout in seconds for the whole request (connect + read). "
        "An explicit `timeout` kwarg passed to `call()` wins over this. "
        "Left empty, the call waits indefinitely.",
    )
    header_ids = fields.One2many(
        "webservice.header",
        "res_id",
        string="Headers",
        domain=lambda self: [("res_model", "=", self._name)],
        help="Static default headers, merged into every call. "
        "An explicit `headers` kwarg passed to `call()` wins over these.",
    )
    querystring_param_ids = fields.One2many(
        "webservice.querystring.param",
        "res_id",
        string="Querystring Params",
        domain=lambda self: [("res_model", "=", self._name)],
        help="Static default querystring params, merged into every call. "
        "An explicit `params` kwarg passed to `call()` wins over these. "
        "A value may contain a '{placeholder}' resolved against the same "
        "values used to fill the URL path (the `url_params` kwarg).",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._set_reference_line_defaults(vals)
            self._handle_tech_name(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._set_reference_line_defaults(vals)
        self._handle_tech_name(vals)
        return super().write(vals)

    def _set_reference_line_defaults(self, vals):
        # `header_ids`/`querystring_param_ids` point to generic
        # (`res_model`/`res_id`) line models: the ORM only auto-fills
        # `res_id` (the declared inverse of the One2many), so `res_model`
        # must be set explicitly here.
        for fname in ("header_ids", "querystring_param_ids"):
            for command in vals.get(fname) or []:
                if command[0] == Command.CREATE:
                    command[2].setdefault("res_model", self._name)

    @api.constrains("auth_type")
    def _check_auth_type(self):
        valid_fields = {
            k: v for k, v in self._fields.items() if hasattr(v, "auth_type")
        }
        for rec in self:
            if rec.auth_type == "none":
                continue
            _fields = [v for v in valid_fields.values() if v.auth_type == rec.auth_type]
            missing = []
            for _field in _fields:
                if not rec[_field.name]:
                    missing.append(_field)
            if missing:
                raise exceptions.UserError(rec._msg_missing_auth_param(missing))

    def _msg_missing_auth_param(self, missing_fields):
        def get_selection_value(fname):
            return self._fields.get(fname).convert_to_export(self[fname], self)

        return self.env._(
            "Webservice '%(name)s' requires '%(auth_type)s' authentication. "
            "However, the following field(s) are not valued: %(fields)s"
        ) % {
            "name": self.name,
            "auth_type": get_selection_value("auth_type"),
            "fields": ", ".join([f.string for f in missing_fields]),
        }

    def _valid_field_parameter(self, field, name):
        extra_params = ("auth_type",)
        return name in extra_params or super()._valid_field_parameter(field, name)

    @api.onchange("name")
    def _onchange_name_for_tech_name(self):
        # Keep this specific name for the method to avoid possible overrides
        # of existing `_onchange_name` methods
        if self.name and not self.tech_name:
            self.tech_name = self.name

    @api.onchange("tech_name")
    def _onchange_tech_name(self):
        if self.tech_name:
            # make sure it's normalized
            self.tech_name = self._normalize_tech_name(self.tech_name)

    def _handle_tech_name(self, vals):
        # make sure technical names are always there
        if not vals.get("tech_name") and vals.get("name"):
            vals["tech_name"] = self._normalize_tech_name(vals["name"])

    def _normalize_tech_name(self, name):
        return self.env["ir.http"]._slugify(name).replace("-", "_")

    def call(self, method, *args, **kwargs):
        kwargs = self._call_prepare(**kwargs)
        _logger.debug("%s: call %s %s %s", self.display_name, method, args, kwargs)
        handler = getattr(self, "_handle_call_for_" + self._get_protocol())
        response = handler(method, *args, **kwargs)
        _logger.debug("%s: response: \n%s", self.display_name, response)
        return response

    def _call_prepare(self, **kwargs):
        """Merge this record's own configured headers/querystring params into kwargs.

        Call-time values (already present in ``kwargs``) win over this
        record's own configuration for matching keys.

        """
        headers = {h.name: h.value for h in self.header_ids}
        headers.update(kwargs.pop("headers", None) or {})
        if headers:
            kwargs["headers"] = headers

        params = {p.name: p.value for p in self.querystring_param_ids}
        params.update(kwargs.pop("params", None) or {})
        if params:
            kwargs["params"] = params

        if self.content_type and "content_type" not in kwargs:
            kwargs["content_type"] = self.content_type

        if self.timeout and "timeout" not in kwargs:
            kwargs["timeout"] = self.timeout

        return kwargs

    def _get_protocol(self):
        return self.protocol

    def _handle_call_for_http(self, method, **kwargs):
        return self._request(method, **kwargs)

    # shortcuts
    def call_get(self, **kwargs):
        return self.call("get", **kwargs)

    def call_post(self, **kwargs):
        return self.call("post", **kwargs)

    def call_put(self, **kwargs):
        return self.call("put", **kwargs)

    def call_delete(self, **kwargs):
        return self.call("delete", **kwargs)

    def _request(self, method, url=None, url_params=None, **kwargs):
        url = self._get_url(url=url, url_params=url_params)
        # ``content_type`` is only consumed by ``_get_headers``: it is not a valid
        # ``requests.request`` kwarg and must not leak into ``new_kwargs`` below.
        content_type = kwargs.pop("content_type", False)
        # Not resolved via `self.timeout` here: by the time `_request` runs,
        # `self` may be the backend even for an endpoint-configured timeout
        # (see `_call_prepare`), so the value must already be in `kwargs`.
        timeout = kwargs.pop("timeout", None)
        url_to_log = self._sanitize_url_for_log(url)
        _logger.info("%s call to %s", method, url_to_log)
        new_kwargs = kwargs.copy()
        new_kwargs.update(
            {
                "auth": self._get_auth(**kwargs),
                "headers": self._get_headers(content_type=content_type, **kwargs),
                "timeout": timeout or None,
            }
        )
        if new_kwargs.get("params"):
            new_kwargs["params"] = self._resolve_query_params(
                new_kwargs["params"], url_params
            )
        # pylint: disable=E8106
        request = requests.request(method, url, **new_kwargs)
        request.raise_for_status()
        return request

    def _sanitize_url_for_log(self, url):
        return sanitize_url_for_log(url)

    def _get_auth(self, auth=False, **kwargs):
        if auth:
            return auth
        handler = getattr(self, "_get_auth_for_" + self.auth_type, None)
        return handler(**kwargs) if handler else None

    def _get_auth_for_user_pwd(self, **kw):
        if self.username and self.password:
            return self.username, self.password
        return None

    def _get_headers(self, content_type=False, headers=False, **kwargs):
        headers = headers or {}
        if content_type or self.content_type:
            result = {
                "Content-Type": content_type or self.content_type,
            }
        else:
            result = {}
        handler = getattr(self, "_get_headers_for_" + self.auth_type, None)
        if handler:
            headers.update(handler(**kwargs))
        result.update(headers)
        return result

    def _get_headers_for_api_key(self, **kw):
        return {self.api_key_header: self.api_key}

    def _get_url(self, url=None, url_params=None, **kwargs):
        base = self._get_base_url()
        if not url:
            url = base
        elif not url.startswith(base):
            if not url.startswith("http"):
                url = f"{base.rstrip('/')}/{url.lstrip('/')}"
            else:
                # TODO: if url is given, we should validate the domain
                # to avoid abusing a webservice backend for different calls.
                pass

        url_params = url_params or kwargs
        return url.format(**url_params)

    def _resolve_query_params(self, params, url_params):
        url_params = url_params or {}
        return {
            name: value.format(**url_params) if isinstance(value, str) else value
            for name, value in params.items()
        }

    def _get_base_url(self):
        """Return the base url requests are relative to.

        To be implemented by models inheriting this mixin.

        """
        raise NotImplementedError
