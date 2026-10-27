# Copyright 2026 Quartile (https://www.quartile.co)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class EndpointEndpoint(models.Model):
    _name = "endpoint.endpoint"
    _inherit = [
        "api.log_collection.mixin",
        "endpoint.endpoint",
    ]
