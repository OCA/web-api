This module provides the ``webservice.backend`` model with its authentication
(public, username/password, API key) and HTTP call features (``get``/``post``/``put``/``delete``).

It has no dependency on ``component`` or ``server_environment``, so it can be used
as a lightweight building block by any module needing to configure and call
an outbound webservice, without pulling in extra frameworks.

On top of a backend, you can configure specific, named ``webservice.endpoint``
records via the UI, instead of only building calls in Python via
``webservice.backend.call(method, url_args, ...)``. Each endpoint bundles a
required description, a fixed HTTP method and relative path (appended to the
backend URL), static headers, and an optional authentication override, fully
independent from the backend's. Endpoints are called with ``endpoint.call(...)``;
calling the backend directly with ``backend.call(method, ...)`` remains fully
supported.
