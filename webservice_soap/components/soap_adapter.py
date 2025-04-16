import logging

from requests import Session
from requests.auth import HTTPBasicAuth
from zeep import Client, Settings
from zeep.transports import Transport

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class SoapAdapter(Component):
    _name = "base.soap"
    _inherit = "base.webservice.adapter"
    _webservice_protocol = "soap"

    def _configure_client(self):
        settings = Settings(
            strict=False,
            xml_huge_tree=True,
        )
        session = Session()
        self._session_auth(session)

        return Client(
            wsdl=self.collection.url,
            transport=Transport(session=session),
            settings=settings,
            service_name=self.collection.soap_service_name,
            port_name=self.collection.soap_port_name,
        )

    def _session_auth(self, session):
        if self.collection.auth_type == "user_pwd":
            session.auth = HTTPBasicAuth(
                self.collection.username, self.collection.password
            )
        elif self.collection.auth_type == "api_key":
            session.headers.update(
                {self.collection.api_key_header: self.collection.api_key}
            )

    def __getattr__(self, attr):
        client = self._configure_client()
        service = client.service
        return getattr(service, attr)
