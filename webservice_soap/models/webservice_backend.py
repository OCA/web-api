from odoo import fields, models


class WebserviceBackend(models.Model):
    _inherit = "webservice.backend"

    protocol = fields.Selection(
        selection_add=[
            ("soap", "SOAP"),
        ],
    )
    soap_service_name = fields.Char(
        help="The service name for the service binding. "
             "Defaults to the first service in the WSDL document."
    )
    soap_port_name = fields.Char(
        help="The port name for the default binding. Defaults to the "
             "first port defined in the service element in the WSDL document."
    )
