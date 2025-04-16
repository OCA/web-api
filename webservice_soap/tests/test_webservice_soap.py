from odoo import modules

from odoo.addons.webservice.tests.common import CommonWebService
from .soap_test_server import SoapTestServer


class TestSoapService(CommonWebService):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.wsdl_file_path = "%s/tests/hello.wsdl" % modules.get_module_path(
            "webservice_soap"
        )
        cls.soap_server = SoapTestServer(cls.wsdl_file_path)
        cls.soap_server.start()

    @classmethod
    def tearDownClass(cls):
        cls.soap_server.stop()
        super().tearDownClass()

    def _setup_records(self):
        super()._setup_records()
        self.soap_backend = self.env["webservice.backend"].create(
            {
                "name": "SOAP Test Service",
                "protocol": "soap",
                "url": self.wsdl_file_path,
                "tech_name": "soap_test",
                "auth_type": "none",
            }
        )
        return self.soap_backend

    def test_soap_call(self):
        result = self.soap_backend.call("sayHello", "John")
        self.assertEqual(result, "Hello John!")
