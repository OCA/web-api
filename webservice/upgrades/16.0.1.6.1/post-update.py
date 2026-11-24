# Copyright 2026 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from openupgradelib import openupgrade

from odoo import _, exceptions


@openupgrade.migrate()
def migrate(env, version):
    module = env["ir.module.module"].search([("name", "=", "webservice_server_env")])
    if not module:
        raise exceptions.UserError(
            _(
                "The 'webservice_server_env' module is not available. "
                "It is required to preserve the server environment managed "
                "fields of 'webservice.backend'. Make it available on the "
                "addons path before upgrading 'webservice'."
            )
        )
    if module.state == "uninstalled":
        module.button_install()
