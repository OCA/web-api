# Copyright 2026 Camptocamp SA
# @author Simone Orsi <simahawk@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class WebserviceQueryStringParam(models.Model):
    """A static default querystring param for a webservice backend or endpoint.

    Sent as an actual HTTP querystring param (``requests``' ``params=``), not
    to be confused with the ``url_params`` kwarg accepted by ``call()``,
    which fills ``{placeholder}`` tokens in the URL path itself. A param's
    ``value`` here may still contain such a ``{placeholder}``: it is resolved
    against the same substitution values before the request is sent.

    Generic (``res_model``/``res_id``) so it can be attached to any model
    inheriting ``webservice.request.mixin`` - see ``querystring_param_ids``
    on the mixin.

    """

    _name = "webservice.querystring.param"
    _description = "WebService Querystring Param"

    res_model = fields.Char(required=True, index=True)
    res_id = fields.Many2oneReference(
        string="Record", model_field="res_model", required=True, index=True
    )
    name = fields.Char(required=True)
    value = fields.Char(required=True)
