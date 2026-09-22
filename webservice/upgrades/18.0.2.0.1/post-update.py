# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

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
    icp = env["ir.config_parameter"].sudo()
    if not icp.search_count([("key", "=", CONTENT_ONLY_COMPAT_PARAM)]):
        icp.set_param(CONTENT_ONLY_COMPAT_PARAM, "1")
