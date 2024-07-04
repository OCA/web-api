# Copyright 2024 Camptocamp (http://camptocamp.com)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

{
    "name": "Endpoint JSONifier",
    "summary": "Allow to configure jsonifier parsers on endpoints",
    "version": "14.0.1.0.0",
    "category": "Uncategorized",
    "website": "https://github.com/OCA/web-api",
    "author": "Camptocamp, Odoo Community Association (OCA)",
    "maintainers": ["SilvioC2C", "simahawk"],
    "license": "LGPL-3",
    "installable": True,
    "depends": ["endpoint", "jsonifier"],
    "data": [
        "views/endpoint_endpoint.xml",
    ],
}
