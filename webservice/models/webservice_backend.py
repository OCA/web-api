# Copyright 2020 Creu Blanca
# Copyright 2022 Camptocamp SA
# @author Simone Orsi <simahawk@gmail.com>
# @author Alexandre Fayolle <alexandre.fayolle@camptocamp.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging

from odoo import api, fields, models
from odoo.tools import config

_logger = logging.getLogger(__name__)

# Backward-compat switch for the `content_only` default removal on `_request`.
# Existing databases get it set (see `webservice`'s `18.0.2.0.1` upgrade
# script) to keep returning only the response content; new installs get the
# full `requests.Response` object with no param set. Safe to delete once
# calling code has been adapted; the code checking it can then be dropped
# too.
CONTENT_ONLY_COMPAT_PARAM = "webservice.request_content_only"


class WebserviceBackend(models.Model):
    _name = "webservice.backend"
    _inherit = [
        "webservice.backend",
        "collection.base",
    ]

    auth_type = fields.Selection(
        selection_add=[("oauth2", "OAuth2")],
        ondelete={"oauth2": "cascade"},
    )
    oauth2_flow = fields.Selection(
        [
            ("backend_application", "Backend Application (Client Credentials Grant)"),
            ("web_application", "Web Application (Authorization Code Grant)"),
        ],
        readonly=False,
    )
    oauth2_clientid = fields.Char(string="Client ID", auth_type="oauth2")
    oauth2_client_secret = fields.Char(string="Client Secret", auth_type="oauth2")
    oauth2_token_url = fields.Char(string="Token URL", auth_type="oauth2")
    oauth2_authorization_url = fields.Char(string="Authorization URL")
    oauth2_audience = fields.Char(
        string="Audience"
        # no auth_type because not required
    )
    oauth2_scope = fields.Char(help="scope of the the authorization")
    oauth2_token = fields.Char(help="the OAuth2 token (serialized JSON)")
    redirect_url = fields.Char(
        compute="_compute_redirect_url",
        help="The redirect URL to be used as part of the OAuth2 authorisation flow",
    )
    oauth2_state = fields.Char(
        help="random key generated when authorization flow starts "
        "to ensure that no CSRF attack happen"
    )

    @api.onchange("auth_type")
    def _onchange_auth_type(self):
        # Keep `oauth2_flow` in sync in the UI as the user edits `auth_type`,
        # regardless of whether `server_environment` is installed (see
        # `create`/`write` below for the same guarantee on any other write).
        if self.auth_type != "oauth2":
            self.oauth2_flow = False

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.filtered(
            lambda r: r.auth_type != "oauth2" and r.oauth2_flow
        ).oauth2_flow = False
        return records

    def write(self, vals):
        res = super().write(vals)
        if "auth_type" in vals:
            self.filtered(
                lambda r: r.auth_type != "oauth2" and r.oauth2_flow
            ).oauth2_flow = False
        return res

    def call(self, method, *args, **kwargs):
        if not self.auth_type.startswith("oauth2"):
            return super().call(method, *args, **kwargs)
        # NOTE: oauth2 still relies on `component` for now, until it gets
        # extracted to its own module and reworked to drop that dependency too.
        _logger.debug("backend %s: call %s %s %s", self.name, method, args, kwargs)
        response = getattr(self._get_adapter(), method)(*args, **kwargs)
        _logger.debug("backend %s: response: \n%s", self.name, response)
        return response

    def _get_adapter(self):
        with self.work_on(self._name) as work:
            return work.component(
                usage="webservice.request",
                webservice_protocol=self._get_adapter_protocol(),
            )

    def _request(self, method, url=None, url_params=None, **kwargs):
        self._pop_deprecated_content_only_kwarg(kwargs)
        response = super()._request(method, url=url, url_params=url_params, **kwargs)
        if self._get_request_content_only():
            return response.content
        return response

    def _pop_deprecated_content_only_kwarg(self, kwargs):
        """Drop the removed ``content_only`` call argument, warning if used.

        It used to switch between returning the raw response content or the
        full ``requests.Response`` object per call. It's gone: the full
        response is always returned now, controlled only (and temporarily)
        by the ``CONTENT_ONLY_COMPAT_PARAM`` system parameter for the whole
        database - not something to keep sprinkling through call sites.
        """
        if "content_only" in kwargs:
            kwargs.pop("content_only")
            _logger.warning(
                "%s: the 'content_only' argument is no longer supported "
                "and was ignored; the full response object is always "
                "returned now. Remove it from the calling code.",
                self.display_name,
            )

    def _get_request_content_only(self):
        """Whether to return only the response content (legacy behavior).

        See ``CONTENT_ONLY_COMPAT_PARAM``.
        """
        content_only = bool(
            self.env["ir.config_parameter"].sudo().get_param(CONTENT_ONLY_COMPAT_PARAM)
        )
        if content_only:
            _logger.warning(
                "%s: returning only the response content because the "
                "'%s' system parameter is set (kept for backward "
                "compatibility after upgrade). Delete it once the calling "
                "code is adapted to use the full response object.",
                self.display_name,
                CONTENT_ONLY_COMPAT_PARAM,
            )
        return content_only

    def _get_adapter_protocol(self):
        protocol = self.protocol
        if self.auth_type.startswith("oauth2"):
            protocol += f"+{self.auth_type}-{self.oauth2_flow}"
        return protocol

    @api.depends("auth_type", "oauth2_flow")
    def _compute_redirect_url(self):
        get_param = self.env["ir.config_parameter"].sudo().get_param
        base_url = get_param("web.base.url")
        if base_url.startswith("http://") and not config["test_enable"]:
            _logger.warning(
                "web.base.url is configured in http. Oauth2 requires using https"
            )
            base_url = base_url[len("http://") :]
        if not base_url.startswith("https://"):
            base_url = f"https://{base_url}"
        for rec in self:
            if rec.auth_type == "oauth2" and rec.oauth2_flow == "web_application":
                rec.redirect_url = f"{base_url}/webservice/{rec.id}/oauth2/redirect"
            else:
                rec.redirect_url = False

    def button_authorize(self):
        _logger.info("Button OAuth2 Authorize")
        authorize_url = self._get_adapter().redirect_to_authorize()
        _logger.info("Redirecting to %s", authorize_url)
        return {
            "type": "ir.actions.act_url",
            "url": authorize_url,
            "target": "self",
        }
