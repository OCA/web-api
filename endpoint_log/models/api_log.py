# Copyright 2026 Quartile (https://www.quartile.co)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from traceback import format_exception

from werkzeug.exceptions import HTTPException

from odoo import api, models


class APILog(models.Model):
    _inherit = "api.log"

    @api.model
    def _selection_collection_ref(self):
        collections = super()._selection_collection_ref()
        endpoint_model = self.env["endpoint.endpoint"]
        collections.append((endpoint_model._name, endpoint_model._description))
        return collections

    def _prepare_log_response(self, response):
        # For a plain Odoo route, ``ir.http._handle_error`` (called by
        # ``log_exception``) returns the HTTP exception itself, not a response.
        if isinstance(response, HTTPException):
            response = response.get_response()
        return super()._prepare_log_response(response)

    def _prepare_log_exception(self, exception):
        if not isinstance(exception, HTTPException):
            return super()._prepare_log_exception(exception)
        # Log the response the exception renders: an exception may override
        # ``get_response()`` (e.g. endpoint's ``RequestValidationError``), which
        # ``code``, ``get_headers()`` and ``get_body()`` do not reflect.
        values = self._prepare_log_response(exception.get_response())
        values["stack_trace"] = "".join(format_exception(exception))
        return values
