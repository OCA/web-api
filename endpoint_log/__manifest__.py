# Copyright 2026 Quartile (https://www.quartile.co)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Endpoint Log",
    "summary": "Log endpoint requests in database",
    "version": "19.0.1.0.0",
    "license": "AGPL-3",
    "development_status": "Alpha",
    "author": "Quartile, Odoo Community Association (OCA)",
    "maintainers": ["AungKoKoLin1997"],
    "website": "https://github.com/OCA/web-api",
    "category": "Tools",
    "depends": ["api_log", "endpoint"],
    "data": [
        "views/endpoint_endpoint_views.xml",
        "views/endpoint_log_views.xml",
    ],
}
