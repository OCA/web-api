# Copyright 2025 feihu.zhang
# @author: feihu.zhang <feihu.zhang@live.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models


class EndpointMixin(models.AbstractModel):
    _inherit = "endpoint.mixin"

    def _selection_auth_type(self):
        return super()._selection_auth_type() + [("bearer", "Bearer")]

    def _validate_request(self, request):
        super()._validate_request(request)
        if self.auth_type == "bearer":
            request.env["ir.http"]._auth_method_bearer()
        return
