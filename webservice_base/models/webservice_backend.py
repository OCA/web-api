# Copyright 2020 Creu Blanca
# Copyright 2022 Camptocamp SA
# @author Simone Orsi <simahawk@gmail.com>
# @author Alexandre Fayolle <alexandre.fayolle@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
import logging

from odoo import _, api, exceptions, fields, models

_logger = logging.getLogger(__name__)


class WebserviceBackend(models.Model):
    _name = "webservice.backend"
    _inherit = ["webservice.request.adapter"]
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
    connect_timeout = fields.Integer(default=5, help="In seconds")
    read_timeout = fields.Integer(default=30, help="In seconds")
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
    company_id = fields.Many2one("res.company", string="Company")

    @api.model
    def get_by_tech_name(self, tech_name):
        backend = self.search(
            [
                ("tech_name", "=", tech_name),
                "|",
                ("company_id", "=", self.env.company.id),
                ("company_id", "=", False),
            ],
            limit=1,
            order="company_id desc, id desc",
        )
        if not backend:
            raise exceptions.UserError(
                _("No WebService Backend found for tech name '%(tech_name)s'.")
                % {"tech_name": tech_name}
            )
        return backend

    @api.constrains("auth_type")
    def _check_auth_type(self):
        all_fields = self._fields.items()
        auth_fields = [x for x in all_fields if hasattr(x[1], "auth_type")]
        for rec in self:
            needed_fields = [x for x in auth_fields if x[1].auth_type == rec.auth_type]
            missing_fields = [x for x in needed_fields if not rec[x[0]]]
            if needed_fields and missing_fields:
                missing = [x[1] for x in missing_fields]
                raise exceptions.UserError(rec._msg_missing_auth_param(missing))

    def _msg_missing_auth_param(self, missing_fields):
        def get_selection_value(fname):
            return self._fields.get(fname).convert_to_export(self[fname], self)

        return _(
            "Webservice '%(name)s' requires '%(auth_type)s' authentication. "
            "However, the following field(s) are not set: %(fields)s"
        ) % {
            "name": self.name,
            "auth_type": get_selection_value("auth_type"),
            "fields": ", ".join([f.string for f in missing_fields]),
        }

    # TODO: remove?
    def _valid_field_parameter(self, field, name):
        extra_params = ("auth_type",)
        return name in extra_params or super()._valid_field_parameter(field, name)

    def call(self, method, *args, **kwargs):
        _logger.debug("backend %s: call %s %s %s", self.name, method, args, kwargs)
        response = getattr(self, method)(*args, **kwargs)
        _logger.debug("backend %s: response: \n%s", self.name, response)
        return response
