# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

from odoo.tools import parse_version

CONTENT_ONLY_COMPAT_PARAM = "webservice.request_content_only"


@openupgrade.migrate()
def migrate(env, version):
    """Preserve the pre-upgrade behavior of HTTP webservice calls.

    Before this version, ``webservice.backend.call()`` (and friends)
    returned only the response content (raw bytes) by default. That default
    is gone: calls now always return the full ``requests.Response`` object.

    Existing databases get ``CONTENT_ONLY_COMPAT_PARAM`` set so their
    calling code keeps working unchanged until it's adapted; new installs
    never get it, so they see the new behavior right away. Leave the
    parameter unset (or delete it) once the calling code is updated.
    """
    # Databases coming from 18.0 >= 18.0.2.0.1 already went through the same
    # upgrade step there: don't set the parameter back if it was removed.
    if version.startswith("18.0.") and parse_version(version) >= parse_version(
        "18.0.2.0.1"
    ):
        return
    icp = env["ir.config_parameter"].sudo()
    if not icp.search_count([("key", "=", CONTENT_ONLY_COMPAT_PARAM)]):
        icp.set_param(CONTENT_ONLY_COMPAT_PARAM, "1")
