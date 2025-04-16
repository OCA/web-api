{
    "name": "Webservice SOAP",
    "summary": """
        Defines webservice to manage soap sevices""",
    "version": "12.0.1.0.0",
    "license": "AGPL-3",
    "author": "ForgeFlow, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/web-api",
    "depends": ["webservice"],
    "data": [
        "views/webservice_backend_views.xml",
    ],
    "external_dependencies": {"python": ["zeep"]},
    "installable": True,
    "application": False,
}
