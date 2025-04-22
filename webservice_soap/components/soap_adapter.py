import logging

from requests import Session
from requests.auth import HTTPBasicAuth
from zeep import Client, Settings
from zeep.transports import Transport

from odoo import _
from odoo.exceptions import ValidationError
from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class SoapAdapter(Component):
    _name = "base.soap"
    _inherit = "base.webservice.adapter"
    _webservice_protocol = "soap"

    def _get_settings(self):
        return Settings(
            strict=False,
            xml_huge_tree=True,
        )

    def _get_session(self):
        if self.collection.auth_type == "user_pwd":
            if not self.collection.username and not self.collection.password:
                raise ValidationError(_("Missing username and/or password"))
            session = Session()
            session.auth = HTTPBasicAuth(
                self.collection.username,
                self.collection.password
            )
            return session
        return None

    def _prepare_client(self):
        client_config_dict = {
            "wsdl": self.collection.url,
        }
        settings = self._get_settings()
        if settings:
            client_config_dict['settings'] = settings
        session = self._get_session()
        if session:
            client_config_dict['transport'] = Transport(session=session)
        if self.collection.soap_service_name:
            client_config_dict['service_name'] = self.collection.soap_service_name
        if self.collection.soap_port_name:
            client_config_dict['port_name'] = self.collection.soap_port_name
        return client_config_dict

    def _get_client(self):
        return Client(
            **self._prepare_client()
        )

    def __getattr__(self, attr):
        if getattr(self, attr):
            return getattr(self, attr)
        client = self._get_client()
        service = client.service
        return getattr(service, attr)
