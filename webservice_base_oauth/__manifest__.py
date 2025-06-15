# Copyright 2020 Creu Blanca
# Copyright 2022 Camptocamp SA
# @author Simone Orsi <simahawk@gmail.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "OAUth support for WebService Base",
    "summary": "Adds OAuth support to webservice backends",
    "version": "18.0.1.1.0",
    "license": "LGPL-3",
    "development_status": "Production/Stable",
    "maintainers": ["etobella"],
    "author": "Creu Blanca, Camptocamp, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/web-api",
    "depends": ["webservice_base"],
    "external_dependencies": {"python": ["requests-oauthlib", "oauthlib", "responses"]},
    "data": ["views/webservice_backend.xml"],
}
