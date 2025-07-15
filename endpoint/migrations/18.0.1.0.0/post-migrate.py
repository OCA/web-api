# Copyright 2025 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Force update endpoint_route table.

    New params like `readonly` should be added to the stored routes.
    """
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    model = env["endpoint.endpoint"]
    records = model.sudo().search([])
    records._handle_registry_sync()
    _logger.info("Forced endpoint route sync on %s records", model._name)
