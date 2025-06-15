This module creates WebService frameworks to be used globally.

It introduces support for HTTP Request protocol.
The webservice HTTP call returns by default the content of the response.
A context 'content_only' can be passed to get the full response object.

It comes with no additional dependencies.
For the original implementation relying on `component` objects,
see the `webservice` addon module.

This work is derived from that module,
removing the `component` and `server_env` dependencies to make it lighter.
As a design decision, using `component` seems to an an additional abstraction layer
(and dependency) that brings little benefit, and removing it brings the implementation
closer to Odoo's framework design patterns.
