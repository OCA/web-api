# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from contextlib import contextmanager
from unittest import mock
from urllib.parse import urlparse

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
            queue_job__no_delay=True,
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


@contextmanager
def mock_cursor(cr):
    # Preserve the original methods and attributes
    org_close = cr.close
    org_autocommit = cr._cnx.autocommit
    org_commit = cr.commit

    try:
        # Mock methods and attributes
        cr.close = mock.Mock()
        cr.commit = mock.Mock()
        # Mocking the autocommit attribute
        mock_autocommit = mock.PropertyMock(return_value=False)
        type(cr._cnx).autocommit = mock_autocommit

        # Mock the cursor method to return the current cr
        with mock.patch("odoo.sql_db.Connection.cursor", return_value=cr):
            yield cr

    finally:
        # Restore the original methods and attributes
        cr.close = org_close
        cr.commit = org_commit
        # Restore the original autocommit property
        type(cr._cnx).autocommit = org_autocommit
