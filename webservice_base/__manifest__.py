# Copyright 2020 Creu Blanca
# Copyright 2022 Camptocamp SA
# @author Simone Orsi <simahawk@gmail.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "WebService Base",
    "summary": """Defines webservice abstract definition to be used generally""",
    "version": "18.0.1.1.0",
    "license": "LGPL-3",
    "development_status": "Production/Stable",
    "maintainers": ["etobella"],
    "author": "Creu Blanca, Camptocamp, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/web-api",
    "depends": ["base"],
    "external_dependencies": {"python": ["requests-oauthlib", "oauthlib", "responses"]},
    "data": [
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "views/webservice_backend.xml",
    ],
    "demo": [],
}
