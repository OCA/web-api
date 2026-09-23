# Copyright 2020 Creu Blanca
# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "WebService Core",
    "summary": """Webservice backend: auth & call features, no extra dependencies""",
    "version": "18.0.1.0.1",
    "license": "AGPL-3",
    "development_status": "Production/Stable",
    "maintainers": ["simahawk"],
    "author": "Creu Blanca, Camptocamp, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/web-api",
    "depends": ["base"],
    "external_dependencies": {"python": ["requests", "openupgradelib"]},
    "data": [
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "views/webservice_backend.xml",
    ],
    "pre_init_hook": "pre_init_hook",
}
