# Copyright 2026 Quartile (https://www.quartile.co)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    "name": "Endpoint JSON2",
    "summary": "Declarative JSON-2 API endpoints on the endpoint stack",
    "version": "19.0.1.0.0",
    "license": "LGPL-3",
    "development_status": "Alpha",
    "author": "Quartile, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/web-api",
    "category": "Technical",
    "depends": ["endpoint"],
    "data": [
        "security/ir.model.access.csv",
        "views/endpoint_views.xml",
    ],
    "demo": ["demo/endpoint_json2_demo.xml"],
    "installable": True,
    "maintainers": ["yostashiro", "aungkokolin1997"],
}
