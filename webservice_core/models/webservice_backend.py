# Copyright 2020 Creu Blanca
# Copyright 2022 Camptocamp SA
# @author Simone Orsi <simahawk@gmail.com>
# @author Alexandre Fayolle <alexandre.fayolle@camptocamp.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class WebserviceBackend(models.Model):
    _name = "webservice.backend"
    _inherit = ["webservice.request.mixin"]
    _description = "WebService Backend"

    name = fields.Char(required=True)
    url = fields.Char(required=True)
    company_id = fields.Many2one("res.company", string="Company")

    def _get_base_url(self):
        return self.url
