# Copyright 2022 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).


class EndpointHandlerNotFound(Exception):
    """Raise when an endpoint handler is not found.

    To register an handler, use::

        registry.register_endpoint_handler(name, ctrl_klass, method_name)
    """
