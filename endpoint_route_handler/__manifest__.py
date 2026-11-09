# Copyright 2021 Camptocamp SA
# Copyright 2026 Open2S (<https://www.open2s.com>)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "Endpoint route handler",
    "summary": """Provide mixin and tool to generate custom endpoints on the fly.""",
    "version": "20.0.1.0.0",
    "license": "LGPL-3",
    "development_status": "Beta",
    "author": "Camptocamp,Open2S,Odoo Community Association (OCA)",
    "maintainers": ["simahawk"],
    "website": "https://github.com/OCA/web-api",
    "depends": ["base"],
    "data": [
        "security/ir.access.csv",
    ],
    "post_init_hook": "post_init_hook",
}
