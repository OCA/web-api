# Copyright 2020 Creu Blanca
# Copyright 2022 Camptocamp SA
# @author Simone Orsi <simahawk@gmail.com>
# @author Alexandre Fayolle <alexandre.fayolle@camptocamp.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class WebserviceBackend(models.Model):
    _name = "webservice.backend"
    _inherit = ["webservice.request.mixin"]
    _description = "WebService Backend"
    _sql_constraints = [
        (
            "tech_name_uniq",
            "unique(tech_name)",
            "`tech_name` must be unique!",
        )
    ]

    name = fields.Char(required=True)
    url = fields.Char(required=True)
    company_id = fields.Many2one("res.company", string="Company")
    endpoint_ids = fields.One2many(
        "webservice.endpoint", "backend_id", string="Endpoints"
    )
    endpoint_count = fields.Integer(compute="_compute_endpoint_count")

    def _get_base_url(self):
        return self.url

    @api.depends("url")
    def _compute_full_url_display(self):
        return super()._compute_full_url_display()

    def _get_secret_names(self):
        # Endpoint calls are logged by the backend, with the endpoint's
        # headers and params merged in.
        header_names, param_names = super()._get_secret_names()
        for endpoint in self.endpoint_ids:
            endpoint_headers, endpoint_params = endpoint._get_own_secret_names()
            header_names |= endpoint_headers
            param_names |= endpoint_params
        return header_names, param_names

    def _compute_endpoint_count(self):
        data = self.env["webservice.endpoint"]._read_group(
            [("backend_id", "in", self.ids)], ["backend_id"], ["__count"]
        )
        mapped_data = {backend.id: count for backend, count in data}
        for rec in self:
            rec.endpoint_count = mapped_data.get(rec.id, 0)

    def action_view_endpoints(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "webservice_core.webservice_endpoint_act_window"
        )
        action["domain"] = [("backend_id", "=", self.id)]
        action["context"] = {"default_backend_id": self.id}
        return action
