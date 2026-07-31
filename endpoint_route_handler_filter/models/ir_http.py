# Copyright 2021 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import logging
import os

from odoo import models, tools

_logger = logging.getLogger(__name__)


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _endpoint_routing_rules_kwargs(cls):
        result = super()._endpoint_routing_rules_kwargs()
        group_filter = tools.config.get(
            "odoo_endpoint_route_handler_filter"
        ) or os.getenv("ODOO_ENDPOINT_ROUTE_HANDLER_FILTER_GROUP")
        no_group_filter = tools.config.get(
            "odoo_endpoint_route_handler_ignore"
        ) or os.getenv("ODOO_ENDPOINT_ROUTE_HANDLER_FILTER_IGNORE")
        if not group_filter and not no_group_filter:
            return result
        where = result.get("where")
        if where:
            where += " AND "
        else:
            where = "WHERE "
        conditions = []
        if group_filter:
            group_filter_sql = "','".join(group_filter.split(","))
            conditions.append(f"route_group in ('{group_filter_sql}')")
        if no_group_filter:
            no_group_filter_sql = "','".join(no_group_filter.split(","))
            conditions.append(f"route_group not in ('{no_group_filter_sql}')")
        result.update({"where": f"{where} {' AND '.join(conditions)}"})
        return result
