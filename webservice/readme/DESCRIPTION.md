This module creates WebService frameworks to be used globally.

The module introduces support for HTTP Request protocol. The webservice HTTP call returns by default the content of the response. A context 'content_only' can be passed to get the full response object.

It builds on top of ``webservice_core`` (which provides the ``webservice.backend``
model with public/username-password/API key authentication) to add OAuth2
authentication and ``server_environment`` support.
