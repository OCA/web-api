# Copyright 2021 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import contextlib

from odoo.tests.common import TransactionCase, tagged
from odoo.tools import DotDict

from odoo.addons.http_routing.tests.common import MockRequest


def _setup_demo_records(env):
    """Create demo records for tests."""
    demo_user = env["res.users"].search([("login", "=", "demo")], limit=1)
    if not demo_user:
        demo_user = env["res.users"].create(
            {"login": "demo", "name": "Marc Demo", "group_ids": [(6, 0, [])]}
        )
    endpoints = env["endpoint.endpoint"]
    endpoints += env["endpoint.endpoint"].create(
        {
            "name": "Demo Endpoint 1",
            "route": "/demo/one",
            "request_method": "GET",
            "exec_mode": "code",
            "code_snippet": 'result = {"response": Response("ok")}',
        }
    )
    endpoints += env["endpoint.endpoint"].create(
        {
            "name": "Demo Endpoint 2",
            "route": "/demo/as_demo_user",
            "request_method": "GET",
            "auth_type": "public",
            "exec_as_user_id": demo_user.id,
            "exec_mode": "code",
            "code_snippet": (
                'result = {"response": Response("My name is: " + user.name)}'
            ),
        }
    )
    endpoints += env["endpoint.endpoint"].create(
        {
            "name": "Demo Endpoint 3",
            "route": "/demo/json_data",
            "request_method": "GET",
            "auth_type": "public",
            "exec_as_user_id": demo_user.id,
            "exec_mode": "code",
            "code_snippet": 'result = {"payload": {"a": 1, "b": 2}}',
        }
    )
    endpoints += env["endpoint.endpoint"].create(
        {
            "name": "Demo Endpoint 4",
            "route": "/demo/raise_not_found",
            "request_method": "GET",
            "auth_type": "public",
            "exec_as_user_id": demo_user.id,
            "exec_mode": "code",
            "code_snippet": "raise werkzeug.exceptions.NotFound()",
        }
    )
    endpoints += env["endpoint.endpoint"].create(
        {
            "name": "Demo Endpoint 5",
            "route": "/demo/raise_validation_error",
            "request_method": "GET",
            "auth_type": "public",
            "exec_as_user_id": demo_user.id,
            "exec_mode": "code",
            "code_snippet": (
                'raise exceptions.ValidationError("Sorry, you cannot do this!")'
            ),
        }
    )
    endpoints += env["endpoint.endpoint"].create(
        {
            "name": "Demo Endpoint 6",
            "route": "/demo/value_from_request",
            "request_method": "GET",
            "auth_type": "public",
            "exec_as_user_id": demo_user.id,
            "exec_mode": "code",
            "code_snippet": (
                'result = {"response": Response(request.params.get("your_name", ""))}'
            ),
        }
    )
    endpoints += env["endpoint.endpoint"].create(
        {
            "name": "Demo Endpoint 7",
            "route": "/demo/bad_method",
            "request_method": "GET",
            "auth_type": "public",
            "exec_as_user_id": demo_user.id,
            "exec_mode": "code",
            "code_snippet": (
                'result = {"payload": "Method used:" + request.httprequest.method}'
            ),
        }
    )
    endpoints += env["endpoint.endpoint"].create(
        {
            "name": "Demo Endpoint 8",
            "route": "/demo/schema",
            "request_method": "POST",
            "request_content_type": "application/json",
            "auth_type": "public",
            "exec_as_user_id": demo_user.id,
            "exec_mode": "code",
            "code_snippet": 'result = {"payload": {"ok": True}}',
            "request_content_schema": (
                "type: object\n"
                "required: [data]\n"
                "properties:\n"
                "  data:\n"
                "    type: array\n"
            ),
        }
    )
    endpoints += env["endpoint.endpoint"].create(
        {
            "name": "Demo Endpoint 9",
            "route": "/demo/schema-xml",
            "request_method": "POST",
            "request_content_type": "application/xml",
            "auth_type": "public",
            "exec_as_user_id": demo_user.id,
            "exec_mode": "code",
            "code_snippet": 'result = {"payload": {"ok": True}}',
            "request_content_schema": (
                '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">'
                '<xs:element name="greeting" type="xs:string"/>'
                "</xs:schema>"
            ),
        }
    )
    endpoints += env["endpoint.endpoint"].create(
        {
            "name": "Demo Endpoint 10",
            "route": "/demo/native_types",
            "request_method": "GET",
            "auth_type": "public",
            "exec_as_user_id": demo_user.id,
            "exec_mode": "code",
            "code_snippet": (
                'result = {"payload": {'
                '"rule_domain": env["ir.rule"]._compute_domain("res.partner"), '
                '"a_date": datetime.date(2026, 1, 15), '
                '"a_datetime": datetime.datetime(2026, 1, 15, 10, 30, 0)'
                "}}"
            ),
        }
    )
    return endpoints


@tagged("-at_install", "post_install")
class CommonEndpoint(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_env()
        cls._setup_records()

    @classmethod
    def _setup_env(cls):
        cls.env = cls.env(context=cls._setup_context())

    @classmethod
    def _setup_context(cls):
        return dict(
            cls.env.context,
            tracking_disable=True,
        )

    @classmethod
    def _setup_records(cls):
        cls.endpoint = _setup_demo_records(cls.env)[0]

    @contextlib.contextmanager
    def _get_mocked_request(
        self, httprequest=None, extra_headers=None, request_attrs=None
    ):
        with MockRequest(self.env) as mocked_request:
            mocked_request.httprequest = (
                DotDict(httprequest) if httprequest else mocked_request.httprequest
            )
            headers = {}
            headers.update(extra_headers or {})
            mocked_request.httprequest.headers = headers
            request_attrs = request_attrs or {}
            for k, v in request_attrs.items():
                setattr(mocked_request, k, v)
            mocked_request.make_response = lambda data, **kw: data
            yield mocked_request
