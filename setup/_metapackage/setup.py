import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo14-addons-oca-web-api",
    description="Meta package for oca-web-api Odoo addons",
    version=version,
    install_requires=[
        'odoo14-addon-endpoint_route_handler',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 14.0',
    ]
)
