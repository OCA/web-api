import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo-addons-oca-web-api",
    description="Meta package for oca-web-api Odoo addons",
    version=version,
    install_requires=[
        'odoo-addon-endpoint_route_handler>=16.0dev,<16.1dev',
        'odoo-addon-webservice>=16.0dev,<16.1dev',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 16.0',
    ]
)
