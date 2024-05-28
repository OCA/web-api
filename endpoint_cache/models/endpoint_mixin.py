# Copyright 2024 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, api, exceptions, fields, models
from odoo.tools import date_utils

from odoo.addons.http_routing.models.ir_http import slugify_one


class EndpointMixin(models.AbstractModel):

    _inherit = "endpoint.mixin"

    cache_policy = fields.Selection(
        selection=[
            ("day", "Daily"),
            ("week", "Weekly"),
            ("month", "Monthly"),
        ],
        default="day",
    )
    # cache_preheat = fields.Boolean()  # TODO

    def _endpoint_cache_make_name(self, ext, suffix=None):
        parts = [
            "endpoint_cache",
            slugify_one(self.name).replace("-", "_"),
        ]
        if suffix:
            parts.append(suffix)
        if ext:
            parts.append(ext)
        return ".".join(parts)

    def _endpoint_cache_get(self, name):
        att = (
            self.env["ir.attachment"]
            .sudo()
            .search(self._endpoint_cache_get_domain(name), limit=1)
        )
        self._logger.debug("_endpoint_cache_get found att=%s", att.id)
        return att.raw

    def _endpoint_cache_get_domain(self, cache_name):
        now = fields.Datetime.now()
        from_datetime = date_utils.start_of(now, self.cache_policy)
        to_datetime = date_utils.end_of(now, self.cache_policy)
        return [
            ("name", "=", cache_name),
            ("res_model", "=", self._name),
            ("res_id", "=", self.id),
            ("create_date", ">=", from_datetime),
            ("create_date", "<=", to_datetime),
        ]

    def _endpoint_cache_store(self, name, raw_data, mimetype=None):
        self._logger.debug("_endpoint_cache_store store att=%s", name)
        if not name.startswith("endpoint_cache"):
            raise exceptions.UserError(_("Cache name must start with 'endpoint_cache'"))
        return (
            self.env["ir.attachment"]
            .sudo()
            .create(
                {
                    "type": "binary",
                    "name": name,
                    "raw": raw_data,
                    "mimetype": mimetype,
                    "res_model": self._name,
                    "res_id": self.id,
                }
            )
        )

    def _endpoint_cache_gc_domain(self, cache_name):
        now = fields.Datetime.now()
        gc_from = date_utils.subtract(now, days=30)
        return [
            ("name", "like", "endpoint_cache%"),
            ("res_model", "=", self._name),
            ("res_id", "=", self.id),
            ("create_date", "<=", gc_from),
        ]

    @api.autovacuum
    def _endpoint_cache_gc(self):
        """Garbage collector for old caches"""
        self.env["ir.attachment"].sudo().search(
            self._endpoint_cache_gc_domain(self._name)
        ).unlink()

    def action_view_cache_attachments(self):
        """Action to view cache attachments"""
        action = self.env["ir.actions.actions"]._for_xml_id("base.action_attachment")
        action["domain"] = self._endpoint_view_cache_domain()
        action["name"] = _("Cache results")
        return action

    def _endpoint_view_cache_domain(self):
        return [
            ("name", "like", "endpoint_cache%"),
            ("res_model", "=", self._name),
            ("res_id", "=", self.id),
        ]
