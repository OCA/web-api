# Copyright 2026 Quartile (https://www.quartile.co)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import functools
import logging
from contextlib import contextmanager

from odoo import models
from odoo.http import request
from odoo.modules.registry import Registry

from odoo.addons.endpoint.controllers.main import EndpointControllerMixin

_logger = logging.getLogger(__name__)


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _get_endpoint_to_log(cls, endpoint):
        """Return the endpoint record served by ``endpoint`` if it logs requests.

        Routes of ``endpoint.mixin`` records are registered by
        ``endpoint_route_handler`` as a ``functools.partial`` of the controller
        method, bound to the model name and the route.
        """
        if not isinstance(endpoint, functools.partial):
            return None
        controller = getattr(endpoint.func, "__self__", None)
        if not isinstance(controller, EndpointControllerMixin):
            return None
        if len(endpoint.args) < 2:
            return None
        model_name, route = endpoint.args[:2]
        model = request.env.get(model_name)
        if model is None or "log_requests" not in model._fields:
            return None
        record = model._find_endpoint(route)
        return record if record.log_requests else None

    @classmethod
    @contextmanager
    def _create_endpoint_log_env(cls, request_env):
        request_registry = request_env.registry
        # `test_log_cr` is set on the registry by the tests (see tests/common.py)
        # to capture the logs with a dedicated cursor.
        test_log_cr = getattr(request_registry, "test_log_cr", None)
        if test_log_cr is not None:
            cr = test_log_cr
        else:
            # Use an independent cursor so that the logs are committed even when
            # the request's transaction is rolled back because of an exception.
            cr = Registry(request_registry.db_name).cursor()
        try:
            yield request_env(cr=cr, su=True)
        finally:
            if test_log_cr is None:
                try:
                    cr.commit()  # pylint: disable=invalid-commit
                finally:
                    cr.close()

    @classmethod
    def _dispatch(cls, endpoint):
        record = cls._get_endpoint_to_log(endpoint)
        if not record:
            return super()._dispatch(endpoint)
        with cls._create_endpoint_log_env(request.env) as log_env:
            try:
                log = log_env["api.log"].log_request(
                    request, {"collection_ref": f"{record._name},{record.id}"}
                )
            except Exception as e:
                _logger.warning("Failed to log request", exc_info=e)
                log = None
            try:
                response = super()._dispatch(endpoint)
            except Exception as response_exc:
                try:
                    log and log.log_exception(response_exc)
                except Exception as e:
                    _logger.warning("Failed to log exception", exc_info=e)
                raise
            try:
                log and log.log_response(response)
            except Exception as e:
                _logger.warning("Failed to log response", exc_info=e)
            return response
