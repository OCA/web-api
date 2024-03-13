# Copyright 2020 Creu Blanca
# Copyright 2022 Camptocamp SA
# @author Simone Orsi <simahawk@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from contextlib import contextmanager

from requests import HTTPError

from odoo import _, api, exceptions, fields, models, registry


class WebserviceBackend(models.Model):

    _name = "webservice.backend"
    _inherit = ["collection.base", "server.env.techname.mixin", "server.env.mixin"]
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
        ],
        default="user_pwd",
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
        required=True,
    )
    save_response = fields.Boolean(
        default=False,
        help=(
            "If enabled, the response for the external call will be saved on the "
            "webservice consumer record",
        ),
    )

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

        return _(
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

    @contextmanager
    def _consumer_record_env(self, record, new_cursor=False):
        """Return the current record in a new transaction or in the the current transaction"""
        if new_cursor:
            with api.Environment.manage():
                with registry(self.env.cr.dbname).cursor() as new_cr:
                    new_env = api.Environment(new_cr, self.env.uid, self.env.context)
                    # in case of error the main transaction will be rollback
                    # in any case we want to save the response payload for
                    # later analysis. Some web-services gives information regarding
                    # the cause of failures
                    yield record.with_env(new_env)
        else:
            yield record

    def call(self, method, *args, consumer_record=None, **kwargs):
        content = False
        status_code = False
        try:
            content = getattr(self._get_adapter(), method)(*args, **kwargs)
            status_code = 200
        except HTTPError as request_error:
            content = request_error.response.content
            status_code = request_error.response.status_code
            raise request_error from request_error
        finally:
            if self.save_response and consumer_record:
                with self._consumer_record_env(
                    consumer_record, new_cursor=status_code != 200
                ) as consumer_record_tx:
                    consumer_record_tx._save_ws_response(content, status_code)
        return content

    def _get_adapter(self):
        with self.work_on(self._name) as work:
            return work.component(
                usage="webservice.request", webservice_protocol=self.protocol
            )

    @property
    def _server_env_fields(self):
        base_fields = super()._server_env_fields
        webservice_fields = {
            "protocol": {},
            "url": {},
            "auth_type": {},
            "username": {},
            "password": {},
            "api_key": {},
            "api_key_header": {},
            "content_type": {},
        }
        webservice_fields.update(base_fields)
        return webservice_fields
