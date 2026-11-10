This module creates WebService frameworks to be used globally.

The module introduces support for HTTP Request protocol. The webservice HTTP call returns the full `requests.Response` object.

It builds on top of ``webservice_core`` (which provides the ``webservice.backend``
model with public/username-password/API key authentication) to add OAuth2
authentication and ``server_environment`` support.
