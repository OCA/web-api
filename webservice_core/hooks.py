# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from openupgradelib import openupgrade

# `webservice.backend`'s base access rule, multi-company rule, and
# non-form views (search/list/action/menu) used to be defined by
# `webservice`, before this module split the base backend out of it. The
# form view keeps its own `webservice.webservice_backend_form_view` XMLID
# (its content changed, but `webservice` still owns and extends it), so it
# is deliberately not in this list.
MOVED_XMLIDS = [
    "access_webservice_backend_edit",
    "rule_webservice_backend_multi_company",
    "webservice_backend_search_view",
    "webservice_backend_tree_view",
    "webservice_backend_act_window",
    "webservice_backend_menu",
]


def pre_init_hook(env):
    """Reuse `webservice`'s pre-split records instead of duplicating them."""
    openupgrade.rename_xmlids(
        env.cr,
        [(f"webservice.{xmlid}", f"webservice_core.{xmlid}") for xmlid in MOVED_XMLIDS],
    )
