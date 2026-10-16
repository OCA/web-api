# Copyright 2026 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import dataclasses
from typing import Any


@dataclasses.dataclass
class ApiCall:
    """State of one request going through the `http_json` pipeline.

    Hooks and params receive the call instead of loose arguments,
    so that new attributes can be added without breaking signatures.

    :param request: the current `odoo.http.Request`
    :param endpoint: the matched endpoint
    :param args: arguments extracted from the URL (eg: `<int:id>`)
    :param params: params passed to the endpoint
        (raw request params before input validation, secure params after)
    :param result: result of the endpoint (validated after output validation)
    :param extra: free storage for hooks and plugins
    """

    request: Any
    endpoint: Any
    args: dict
    params: dict
    result: Any = None
    extra: dict = dataclasses.field(default_factory=dict)

    @property
    def env(self):
        # Always the current env: hooks might update it (eg: context)
        """Current env: hooks might have changed it (eg: context)."""
        return self.request.env

    @property
    def routing(self):
        """Routing of the endpoint: drives the behavior of the pipeline."""
        return self.endpoint.routing

    @property
    def httprequest(self):
        """Shortcut to the werkzeug request."""
        return self.request.httprequest
