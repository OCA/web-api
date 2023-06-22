# Copyright 2022 Foodles (http://www.foodles.co).
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import base64

from odoo import fields, models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT

from odoo.addons.http_routing.models.ir_http import slugify


class WebserviceConsumerMixin(models.AbstractModel):

    _name = "webservice.consumer.mixin"
    _description = "Add fields to save web service responses"

    ws_response_status_code = fields.Integer(
        "Status code",
        help="Web service response HTTP code",
    )
    ws_response_content = fields.Binary(
        "Response",
        attachment=True,
        copy=False,
        help="Web service response content",
    )
    ws_response_date = fields.Datetime(
        "Response date",
        help="Date when the web service response has been saved",
    )
    ws_response_content_filename = fields.Char(
        compute="_compute_ws_response_content_filename"
    )

    def _compute_ws_response_content_filename(self):
        for rec in self:
            if rec.ws_response_date and rec.ws_response_status_code:
                formatted_response_date = slugify(
                    rec.ws_response_date.strftime(DATETIME_FORMAT)
                )
                rec.ws_response_content_filename = "response_%s_%s.json" % (
                    formatted_response_date,
                    str(rec.ws_response_status_code),
                )
            else:
                rec.ws_response_content_filename = ""

    def _save_ws_response(self, content, status_code):
        """
        `content` is response data returned by the HTTP webservice
        to be stored on the consumer record.

        In case of status_code != 200 the odoo transaction is not
        the same as the main transaction in order to save it in any case.

        This method is a good candidate if you want to change state of the
        consumer record according the received error.
        """
        self.ensure_one()
        self.ws_response_content = base64.b64encode(content) if content else False
        self.ws_response_status_code = status_code
        self.ws_response_date = fields.Datetime.now()
