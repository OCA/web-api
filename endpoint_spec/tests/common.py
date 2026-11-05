# Copyright 2026 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from ..decorator import endpoint
from ..spec import EndpointRoute


class Base:
    def helper(self):
        """Public method of the base class: never exposed by conventions."""

    @property
    def boom(self):
        raise AssertionError("Properties must not be evaluated")


class Service(Base):
    @endpoint("GET", path=["/<int:id>", "/<int:id>/get"], auth="public")
    def get(self, id):
        return id

    @endpoint(input="in", output="out")
    def scan(self, barcode):
        return barcode

    @endpoint(["GET", "POST"])
    def multi(self):
        return True

    def not_decorated(self):
        return True

    def _private(self):
        return True


class ServiceChild(Service):
    def scan(self, barcode):
        return super().scan(barcode)

    @endpoint.extend(routing={"api_doc": {"tags": ["child"]}}, output="out2")
    def multi(self):
        return super().multi()


def routes(*pairs):
    """Build the expected `EndpointRoute` tuple from `(paths, methods)` pairs."""
    return tuple(EndpointRoute(paths=tuple(p), methods=tuple(m)) for p, m in pairs)
