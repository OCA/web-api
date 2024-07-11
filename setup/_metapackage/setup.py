import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo14-addons-oca-web-api",
    description="Meta package for oca-web-api Odoo addons",
    version=version,
    install_requires=[
        'odoo14-addon-endpoint',
        'odoo14-addon-endpoint_auth_api_key',
        'odoo14-addon-endpoint_cache',
        'odoo14-addon-endpoint_jsonifier',
        'odoo14-addon-endpoint_route_handler',
        'odoo14-addon-webservice',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 14.0',
    ]
)
