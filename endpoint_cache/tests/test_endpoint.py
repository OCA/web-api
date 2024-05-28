# Copyright 2024 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from freezegun import freeze_time

from odoo import exceptions

from odoo.addons.endpoint.tests.common import CommonEndpoint


class TestEndpoint(CommonEndpoint):
    @classmethod
    def _setup_records(cls):
        super()._setup_records()
        cls.endpoint1 = cls.env.ref("endpoint.endpoint_demo_1")
        cls.endpoint2 = cls.env.ref("endpoint.endpoint_demo_2")

    def test_cache_name(self):
        self.assertEqual(
            self.endpoint1._endpoint_cache_make_name("json"),
            "endpoint_cache.demo_endpoint_1.json",
        )
        self.assertEqual(
            self.endpoint2._endpoint_cache_make_name("json"),
            "endpoint_cache.demo_endpoint_2.json",
        )

    def test_cache_store_bad_name(self):
        with self.assertRaisesRegex(
            exceptions.UserError, "Cache name must start with 'endpoint_cache'"
        ):
            self.endpoint1._endpoint_cache_store("test", b"test")

    def test_cache_store_and_get(self):
        self.endpoint1._endpoint_cache_store("endpoint_cache.test", b"test")
        data = self.endpoint1._endpoint_cache_get("endpoint_cache.test")
        self.assertEqual(data, b"test")

    def test_cache_gc(self):
        dt1 = "2024-07-01 00:00:00"
        with freeze_time(dt1):
            cache1 = self.endpoint1._endpoint_cache_store(
                "endpoint_cache.test", b"test"
            )
            cache1._write(
                {
                    "create_date": dt1,
                }
            )
        dt2 = "2024-07-10 00:00:00"
        with freeze_time(dt2):
            cache2 = self.endpoint1._endpoint_cache_store(
                "endpoint_cache.test2", b"test2"
            )
            cache2._write(
                {
                    "create_date": dt2,
                }
            )
        dt2 = "2024-07-20 00:00:00"
        with freeze_time(dt2):
            cache3 = self.endpoint1._endpoint_cache_store(
                "endpoint_cache.test3", b"test3"
            )
            cache3._write(
                {
                    "create_date": dt2,
                }
            )
        with freeze_time("2024-08-01 00:00:00"):
            self.endpoint1._endpoint_cache_gc()
            self.assertFalse(cache1.exists())
            self.assertTrue(cache2.exists())
            self.assertTrue(cache3.exists())
        with freeze_time("2024-08-12 00:00:00"):
            self.endpoint1._endpoint_cache_gc()
            self.assertFalse(cache1.exists())
            self.assertFalse(cache2.exists())
            self.assertTrue(cache3.exists())
