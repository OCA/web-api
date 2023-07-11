# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "WebService",
    "summary": """
        Defines webservice abstract definition to be used generally""",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "development_status": "Production/Stable",
    "maintainers": ["etobella"],
    "author": "Creu Blanca,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/web-api",
    "depends": ["component", "server_environment"],
    "external_dependencies": {
        "python": [
            "responses",
        ],
    },
    "data": ["security/ir.model.access.csv", "views/webservice_backend.xml"],
    "demo": [],
}
