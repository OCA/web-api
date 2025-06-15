This module creates WebService frameworks to be used globally.

It introduces support for HTTP Request protocol.
The webservice HTTP call returns by default the content of the response.
A `content_only` parameter can be passed to get the full response object.

This addon is a simplified version of the `webservice` module.
In most cases, you can install `webservice_base` instead of `webservice` as a drop-in replacement when you need to define a backend and perform HTTP requests from server-side code.

It comes with no additional dependencies.
For the original implementation relying on `component` objects,
see the `webservice` addon module.

This work is derived from that module,
removing the `component` and `server_env` dependencies to make it lighter.
As a design decision, using `component` seems to an an additional abstraction layer
(and dependency) that brings little benefit, and removing it brings the implementation
closer to Odoo's framework design patterns.

Main differences with `webservice`:

- `webservice_base` focuses on direct usage from Odoo models (no component registry layer).
- It provides a lightweight configuration model (`webservice.backend`) and a request adapter (`webservice.request.adapter`).
- Features that depend on `server_environment` and component-based extensibility are not part of `webservice_base`.
