# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from contextlib import contextmanager
from unittest import mock

import responses
from requests import PreparedRequest, Session

from odoo.tests.common import tagged

from odoo.addons.component.tests.common import TransactionComponentCase


@tagged("-at_install", "post_install")
class CommonWebService(TransactionComponentCase):
    @classmethod
    def _setup_context(cls):
        return dict(
            cls.env.context,
            tracking_disable=True,
            test_queue_job_no_delay=True,
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
        if r.url.startswith("https://localhost.demo.odoo/") or r.url.startswith(
            "https://custom.url"
        ):
            response = responses.Response(r.method, r.url, body=r.body)
            response.status_code = 200
            response.request = r
            response._content = b"{}"
            return response
        return super()._request_handler(s, r, **kw)


@contextmanager
def mock_cursor(cr):
    with mock.patch("odoo.sql_db.Connection.cursor") as mocked_cursor_call:
        org_close = cr.close
        org_autocommit = cr.autocommit
        try:
            cr.close = mock.Mock()
            cr.autocommit = mock.Mock()
            cr.commit = mock.Mock()
            mocked_cursor_call.return_value = cr
            yield
        finally:
            cr.close = org_close
    cr.autocommit = org_autocommit
