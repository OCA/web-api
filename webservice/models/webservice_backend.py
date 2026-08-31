# Copyright 2020 Creu Blanca
# Copyright 2022 Camptocamp SA
# @author Simone Orsi <simahawk@gmail.com>
# @author Alexandre Fayolle <alexandre.fayolle@camptocamp.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging

from odoo import api, exceptions, fields, models
from odoo.tools import config

_logger = logging.getLogger(__name__)


class WebserviceBackend(models.Model):
    _name = "webservice.backend"
    _inherit = ["collection.base"]
    _description = "WebService Backend"

    name = fields.Char(required=True)
    tech_name = fields.Char(required=True)
    protocol = fields.Selection([("http", "HTTP Request")], required=True)
    url = fields.Char(required=True)
    auth_type = fields.Selection(
        selection=[
            ("none", "Public"),
            ("user_pwd", "Username & password"),
            ("api_key", "API Key"),
            ("oauth2", "OAuth2"),
        ],
        required=True,
    )
    username = fields.Char(auth_type="user_pwd")
    password = fields.Char(auth_type="user_pwd")
    api_key = fields.Char(string="API Key", auth_type="api_key")
    api_key_header = fields.Char(string="API Key header", auth_type="api_key")
    oauth2_flow = fields.Selection(
        [
            ("backend_application", "Backend Application (Client Credentials Grant)"),
            ("web_application", "Web Application (Authorization Code Grant)"),
        ],
        readonly=False,
    )
    oauth2_client_auth_method = fields.Selection(
        [
            ("client_secret_basic", "Client ID & Secret (HTTP Basic)"),
            ("custom_header", "Custom Authorization header"),
        ],
        default="client_secret_basic",
        string="Client Authentication",
        help="How the client credentials are presented to the token endpoint.",
    )
    oauth2_clientid = fields.Char(string="Client ID")
    oauth2_client_secret = fields.Char(string="Client Secret")
    oauth2_client_auth_header = fields.Char(
        string="Client Auth Header",
        default="Authorization",
        help="Header name used to send the client credentials when the client "
        "authentication method is a custom Authorization header.",
    )
    oauth2_client_auth_value = fields.Char(
        string="Client Auth Header Value",
        help="Full, static header value sent to the token endpoint when the "
        "client authentication method is a custom Authorization header "
        "(e.g. 'SSWS <token>').",
    )
    oauth2_token_url = fields.Char(string="Token URL", auth_type="oauth2")
    oauth2_token_method = fields.Selection(
        [("post", "POST"), ("get", "GET")],
        default="post",
        string="Token Request Method",
        help="HTTP method used to request the token from the token endpoint. "
        "Most providers use POST; some expose the token endpoint as GET.",
    )
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
    content_type = fields.Selection(
        [
            ("application/json", "JSON"),
            ("application/xml", "XML"),
            ("application/x-www-form-urlencoded", "Form"),
        ],
    )
    company_id = fields.Many2one("res.company", string="Company")

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

    @api.constrains(
        "auth_type",
        "oauth2_client_auth_method",
        "oauth2_clientid",
        "oauth2_client_secret",
    )
    def _check_oauth2_client_secret_basic(self):
        for rec in self:
            if rec.auth_type != "oauth2":
                continue
            if rec.oauth2_client_auth_method != "client_secret_basic":
                continue
            missing = [
                rec._fields[fname]
                for fname in ("oauth2_clientid", "oauth2_client_secret")
                if not rec[fname]
            ]
            if missing:
                raise exceptions.UserError(rec._msg_missing_auth_param(missing))

    @api.constrains(
        "auth_type",
        "oauth2_client_auth_method",
        "oauth2_client_auth_header",
        "oauth2_client_auth_value",
    )
    def _check_oauth2_custom_header(self):
        for rec in self:
            if rec.auth_type != "oauth2":
                continue
            if rec.oauth2_client_auth_method != "custom_header":
                continue
            missing = [
                rec._fields[fname]
                for fname in ("oauth2_client_auth_header", "oauth2_client_auth_value")
                if not rec[fname]
            ]
            if missing:
                raise exceptions.UserError(rec._msg_missing_auth_param(missing))

    def _msg_missing_auth_param(self, missing_fields):
        def get_selection_value(fname):
            return self._fields.get(fname).convert_to_export(self[fname], self)

        return self.env._(
            "Webservice '%(name)s' requires '%(auth_type)s' authentication. "
            "However, the following field(s) are not valued: %(fields)s",
            name=self.name,
            auth_type=get_selection_value("auth_type"),
            fields=", ".join([f.string for f in missing_fields]),
        )

    def _valid_field_parameter(self, field, name):
        extra_params = ("auth_type",)
        return name in extra_params or super()._valid_field_parameter(field, name)

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
