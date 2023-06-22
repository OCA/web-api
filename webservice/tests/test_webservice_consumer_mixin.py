# Copyright 2023 Foodles (http://www.foodles.co).
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
from contextlib import contextmanager
from unittest import mock

import responses
from freezegun import freeze_time
from odoo_test_helper import FakeModelLoader
from requests.exceptions import HTTPError

from odoo import models

from .common import CommonWebService


class TestWebService(CommonWebService):
    @classmethod
    def _setup_records(cls):
        super()._setup_records()
        cls.loader = FakeModelLoader(cls.env, cls.__module__)
        cls.addClassCleanup(cls.loader.restore_registry)
        cls.loader.backup_registry()

        class FakeWebserviceConsumer(models.Model):
            _name = "fake.webservice.consumer"
            _description = "Fake model to store webservice responses"
            _inherit = ["webservice.consumer.mixin"]

        cls.loader.update_registry((FakeWebserviceConsumer,))

        cls.url = "http://localhost.demo.odoo/"
        cls.webservice = cls.env["webservice.backend"].create(
            {
                "name": "WebService",
                "protocol": "http",
                "url": cls.url,
                "content_type": "application/xml",
                "tech_name": "demo_ws",
                "auth_type": "none",
                "save_response": True,
            }
        )

        @contextmanager
        def _consumer_record_no_new_env(self, record, new_cursor=True):
            yield record

        cls._consumer_record_no_new_env = _consumer_record_no_new_env

    @responses.activate
    @freeze_time("2014-06-15 16:24:33")
    def test_web_service_post(self):
        content = "{'test': true}"

        consumer_record = self.env["fake.webservice.consumer"].create({})
        responses.add(responses.POST, self.url, body=content)
        self.webservice.call(
            "post",
            data="demo_response",
            consumer_record=consumer_record,
        )
        self.assertEqual(
            base64.b64decode(consumer_record.ws_response_content).decode(), content
        )
        self.assertEqual(consumer_record.ws_response_status_code, 200)
        self.assertEqual(
            consumer_record.ws_response_content_filename,
            "response_2014-06-15-16-24-33_200.json",
        )

    @responses.activate
    @freeze_time("2024-06-15 16:24:33")
    def test_web_service_with_error(self):
        content = "{'error': 'something goes wrong'}"
        responses.add(responses.POST, self.url, body=content, status=401)
        consumer_record = self.env["fake.webservice.consumer"].create({})
        with self.assertRaisesRegex(HTTPError, "401 Client Error: Unauthorized"):
            with mock.patch(
                "odoo.addons.webservice.models.webservice_backend."
                "WebserviceBackend._consumer_record_env",
                side_effect=self._consumer_record_no_new_env,
            ) as consumer_record_env_mock:
                self.webservice.call(
                    "post",
                    data="demo_response",
                    consumer_record=consumer_record,
                )
            consumer_record_env_mock.assert_called_once_with(
                consumer_record, new_cursor=True
            )

        self.assertEqual(
            base64.b64decode(consumer_record.ws_response_content).decode(), content
        )
        self.assertEqual(consumer_record.ws_response_status_code, 401)
        self.assertEqual(
            consumer_record.ws_response_content_filename,
            "response_2024-06-15-16-24-33_401.json",
        )

    @responses.activate
    def test_web_service_post_no_save(self):
        content = "{'test': true}"
        self.webservice.save_response = False
        consumer_record = self.env["fake.webservice.consumer"].create({})
        responses.add(responses.POST, self.url, body=content)
        self.webservice.call(
            "post", data="demo_response", consumer_record=consumer_record
        )
        self.assertEqual(consumer_record.ws_response_content, False)
        self.assertEqual(consumer_record.ws_response_status_code, False)
        self.assertEqual(consumer_record.ws_response_content_filename, "")

    def test_recall_clear_response_on_error(self):
        content = "{'test': true}"
        consumer_record = self.env["fake.webservice.consumer"].create(
            {
                "ws_response_status_code": 999,
                "ws_response_content": base64.b64encode(content.encode()),
            }
        )
        with mock.patch(
            (
                "odoo.addons.webservice.components.request_adapter."
                "BaseRestRequestsAdapter._get_url"
            ),
            side_effect=Exception("Not an HTTPError"),
        ):
            with mock.patch(
                "odoo.addons.webservice.models.webservice_backend."
                "WebserviceBackend._consumer_record_env",
                side_effect=self._consumer_record_no_new_env,
            ) as consumer_record_env_mock:
                with self.assertRaisesRegex(Exception, "Not an HTTPError"):
                    self.webservice.call(
                        "post",
                        data="demo_response",
                        consumer_record=consumer_record,
                    )
                consumer_record_env_mock.assert_called_once_with(
                    consumer_record, new_cursor=True
                )
        self.assertEqual(consumer_record.ws_response_content, False)
        self.assertEqual(consumer_record.ws_response_status_code, False)
        self.assertEqual(consumer_record.ws_response_content_filename, "")

    def test_consumer_record_env_new_transaction(self):
        record = self.env.user

        with self.webservice._consumer_record_env(
            record, new_cursor=True
        ) as rec_new_tx:
            self.assertEqual(record.id, rec_new_tx.id)
            self.assertNotEqual(record.env.cr, rec_new_tx.env.cr)
