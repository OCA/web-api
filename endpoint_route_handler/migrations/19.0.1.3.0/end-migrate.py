# Copyright 2026 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Register again all routes in sync: their hash is now stable across processes.

    Rows are dropped and created again to enforce the new hash.
    Run at the end of the update: consumer models (eg: `endpoint.endpoint`)
    belong to modules loaded after this one.
    """
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    # No cache: the registry might have been partially loaded when cached
    model_names = env["endpoint.route.handler"]._find_endpoint_route_consumer_models()
    for model_name in model_names:
        records = (
            env[model_name]
            .with_context(active_test=False)
            .search([("registry_sync", "=", True)])
        )
        records._unregister_controllers(clear_cache=False)
        records.filtered("active")._register_controllers(clear_cache=False)
        _logger.info("%s: registered %s routes again", model_name, len(records))
    env.registry.clear_cache("routing")
