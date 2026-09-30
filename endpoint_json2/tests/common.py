# Copyright 2026 Quartile (https://www.quartile.co)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import Command
from odoo.tests.common import TransactionCase, tagged


@tagged("-at_install", "post_install")
class CommonEndpointJson2(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model_partner = cls.env["ir.model"]._get("res.partner")
        cls.group_user = cls.env.ref("base.group_user")
        cls.endpoint = cls._create_endpoint(
            {
                "name": "get_partners",
                "route_group": "test_contacts",
                "json2_description": "Return partner records",
                "json2_method": "search_read",
                "json2_response_fields": "name\nemail",
                "json2_default_domain": "[]",
                "json2_group_ids": [Command.link(cls.group_user.id)],
            }
        )

    @classmethod
    def _create_endpoint(cls, vals):
        # route is required but not precomputed in endpoint_route_handler;
        # auto-derive it until that is fixed upstream.
        defaults = {
            "route_group": "test",
            "exec_mode": "json2",
            "request_method": "POST",
            "request_content_type": "application/json",
            "auth_type": "bearer",
            "json2_model_id": cls.model_partner.id,
            "json2_group_ids": [Command.link(cls.group_user.id)],
        }
        defaults.update(vals)
        defaults.setdefault(
            "route", f"/json2/{defaults['route_group']}/{defaults['name']}"
        )
        return cls.env["endpoint.endpoint"].create(defaults)
