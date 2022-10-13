# Copyright 2021 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import logging
from contextlib import closing

from psycopg2 import ProgrammingError

from odoo import api
from odoo.modules.registry import Registry

_logger = logging.getLogger(__name__)

_REGISTRY_BY_DB = {}


class EndpointRegistry:
    """Registry for endpoints.

    Used to:

    * track registered endpoints
    * track routes to be updated for specific ir.http instances
    * retrieve routing rules to load in ir.http routing map
    """

    __slots__ = ("_mapping", "_http_ids", "_http_ids_to_update")

    def __init__(self):
        # collect EndpointRule objects
        self._mapping = {}
        # collect ids of ir.http instances
        self._http_ids = set()
        # collect ids of ir.http instances that need update
        self._http_ids_to_update = set()

    def get_rules(self):
        return self._mapping.values()

    # TODO: add test
    def get_rules_by_group(self, group):
        for key, rule in self._mapping.items():
            if rule.route_group == group:
                yield (key, rule)

    def add_or_update_rule(self, rule, force=False, init=False):
        """Add or update an existing rule.

        :param rule: instance of EndpointRule
        :param force: replace a rule forcedly
        :param init: given when adding rules for the first time
        """
        key = rule.key
        existing = self._mapping.get(key)
        if not existing or force:
            self._mapping[key] = rule
            if not init:
                self._refresh_update_required()
            return True
        if existing.endpoint_hash != rule.endpoint_hash:
            # Override and set as to be updated
            self._mapping[key] = rule
            if not init:
                self._refresh_update_required()
            return True

    def drop_rule(self, key):
        existing = self._mapping.pop(key, None)
        if not existing:
            return False
        self._refresh_update_required()
        return True

    def routing_update_required(self, http_id):
        return http_id in self._http_ids_to_update

    def _refresh_update_required(self):
        for http_id in self._http_ids:
            self._http_ids_to_update.add(http_id)

    def reset_update_required(self, http_id):
        self._http_ids_to_update.discard(http_id)

    @classmethod
    def registry_for(cls, dbname):
        if dbname not in _REGISTRY_BY_DB:
            _REGISTRY_BY_DB[dbname] = cls()
        return _REGISTRY_BY_DB[dbname]

    @classmethod
    def wipe_registry_for(cls, dbname):
        if dbname in _REGISTRY_BY_DB:
            del _REGISTRY_BY_DB[dbname]

    def ir_http_track(self, _id):
        self._http_ids.add(_id)

    def ir_http_seen(self, _id):
        return _id in self._http_ids

    @staticmethod
    def make_rule(*a, **kw):
        return EndpointRule(*a, **kw)


class EndpointRule:
    """Hold information for a custom endpoint rule."""

    __slots__ = ("key", "route", "endpoint", "routing", "endpoint_hash", "route_group")

    def __init__(self, key, route, endpoint, routing, endpoint_hash, route_group=None):
        self.key = key
        self.route = route
        self.endpoint = endpoint
        self.routing = routing
        self.endpoint_hash = endpoint_hash
        self.route_group = route_group

    def __repr__(self):
        return f"{self.key}: {self.route}" + (
            f"[{self.route_group}]" if self.route_group else ""
        )


setup_signaling = Registry.setup_signaling


def _setup_signaling(self):
    setup_signaling(self)
    if self.in_test_mode():
        return

    with self.cursor() as cr:
        self.endpoint_registry_sequence = -1
        cr.execute("""SELECT 1  FROM pg_class WHERE RELNAME = 'endpoint_version'""")
        if cr.fetchone():
            cr.execute("SELECT last_value FROM endpoint_version")
            self.endpoint_registry_sequence = cr.fetchone()[0]


Registry.setup_signaling = _setup_signaling

check_signaling = Registry.check_signaling


def _check_signaling(self):
    check_signaling(self)
    if self.in_test_mode():
        return self

    with closing(self.cursor()) as cr:
        # TODO  manage endpoint deletion
        try:
            cr.execute("SELECT last_value FROM endpoint_version")
            r = cr.fetchone()[0]
            if getattr(self, "endpoint_registry_sequence", 1) != r:
                _logger.info(
                    "Invalidating the endpoint registry after database signaling"
                    " with version %d",
                    r,
                )
                self.endpoint_registry_sequence = r
                env = api.Environment(cr, 1, {})
                env["endpoint.route.handler"]._check_signaling(
                    self.endpoint_registry_sequence
                )
        except ProgrammingError as pe:
            if pe.pgcode != "42P01":
                raise pe
            _logger.info("enpoint_route_handler not installed on this DB")


Registry.check_signaling = _check_signaling
