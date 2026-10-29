# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from urllib.parse import urlparse

from requests import PreparedRequest, Session

from odoo.tests.common import TransactionCase, tagged


@tagged("-at_install", "post_install")
class CommonWebService(TransactionCase):
    @classmethod
    def _setup_context(cls):
        return dict(
            cls.env.context,
            tracking_disable=True,
        )

    @classmethod
    def _setup_env(cls):
        cls.env = cls.env(context=cls._setup_context())

    @classmethod
    def _setup_records(cls):
        pass

    @classmethod
    def setUpClass(cls):
        cls._super_send = Session.send
        super().setUpClass()
        cls._setup_env()
        cls._setup_records()

    @classmethod
    def _request_handler(cls, s: Session, r: PreparedRequest, /, **kw):
        if urlparse(r.url).netloc in ("localhost.demo.odoo", "custom.url"):
            return cls._super_send(s, r)
        return super()._request_handler(s, r, **kw)
