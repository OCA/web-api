# Copyright 2026 Camptocamp SA (https://www.camptocamp.com).
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import json

import werkzeug.exceptions

from odoo.http import Response


class RequestValidationError(werkzeug.exceptions.HTTPException):
    """Raised when the body fails JSON/XML schema validation.

    Emits ``{"detail": [{"loc", "msg", "type"}, ...]}`` (FastAPI-style) with a
    400 status instead of the generic werkzeug HTML body.

    ``code`` is left as ``None`` on purpose: this makes Odoo treat the
    exception as a ready-made response and run the normal ``post_dispatch``
    hook on it, so route-managed headers (CORS, CSP, ...) are preserved. A real
    ``code`` (e.g. via ``BadRequest``) would route through ``handle_error``
    instead and drop those headers.
    """

    code = None

    def __init__(self, detail):
        super().__init__()
        self.detail = detail

    def get_response(self, environ=None, scope=None):
        return Response(
            json.dumps({"detail": self.detail}),
            status=400,
            mimetype="application/json",
        )
