# Copyright 2026 Camptocamp SA
# @author Simone Orsi <simahawk@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class WebserviceHeader(models.Model):
    """A static default HTTP header for a webservice backend or endpoint.

    Generic (``res_model``/``res_id``) so it can be attached to any model
    inheriting ``webservice.request.mixin``, not just one of them - see
    ``header_ids`` on the mixin.

    """

    _name = "webservice.header"
    _description = "WebService Header"

    res_model = fields.Char(required=True, index=True)
    res_id = fields.Many2oneReference(
        string="Record", model_field="res_model", required=True, index=True
    )
    name = fields.Char(required=True)
    value = fields.Char(required=True)
    secret = fields.Boolean(
        help="The value is a secret (e.g. a token or a key): "
        "it is hidden in the UI and dropped when the database is neutralized.",
    )
