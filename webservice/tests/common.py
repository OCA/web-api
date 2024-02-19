# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from requests import PreparedRequest, Session

from odoo.tests.common import HttpCase, _super_send, tagged

from odoo.addons.component.tests.common import TransactionComponentCase


@tagged("-at_install", "post_install")
class CommonWebService(TransactionComponentCase, HttpCase):
    @classmethod
    def _setup_context(cls):
        return dict(
            cls.env.context, tracking_disable=True, test_queue_job_no_delay=True
        )

    @classmethod
    def _setup_env(cls):
        cls.env = cls.env(context=cls._setup_context())

    @classmethod
    def _setup_records(cls):
        pass

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_env()
        cls._setup_records()

    @classmethod
    def _request_handler(cls, s: Session, r: PreparedRequest, /, **kw):
        if r.url.startswith("http://demo.localhost.odoo") or r.url.startswith(
            "https://custom.url"
        ):
            return _super_send(s, r, **kw)
        return super()._request_handler(s, r, **kw)
