# Copyright 2026 Camptocamp SA
# @author Simone Orsi <simahawk@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging
from urllib.parse import parse_qsl, urlsplit, urlunsplit

from openupgradelib import openupgrade

_logger = logging.getLogger(__name__)


@openupgrade.migrate()
def migrate(env, version):
    """Move any existing querystring in `webservice.backend.url` into records.

    `querystring_param_ids` (available on both backends and endpoints) is
    now the dedicated mechanism for that. The backend's URL keeps sending
    the exact same querystring as before - it's just represented as
    structured `webservice.querystring.param` records now instead of
    being baked into the URL string.

    """
    backends = env["webservice.backend"].search([("url", "like", "%?%")])
    for backend in backends:
        parts = urlsplit(backend.url)
        if not parts.query:
            continue
        query_pairs = parse_qsl(parts.query, keep_blank_values=True)
        clean_url = urlunsplit(
            (parts.scheme, parts.netloc, parts.path, "", parts.fragment)
        )
        backend.url = clean_url
        env["webservice.querystring.param"].create(
            [
                {
                    "res_model": "webservice.backend",
                    "res_id": backend.id,
                    "name": name,
                    "value": value,
                }
                for name, value in query_pairs
            ]
        )
        _logger.info(
            "webservice.backend(%s): moved querystring %r to querystring_param_ids",
            backend.id,
            parts.query,
        )
