This module provides the ``webservice.backend`` model with its authentication
(public, username/password, API key) and HTTP call features (``get``/``post``/``put``).

It has no dependency on ``component`` or ``server_environment``, so it can be used
as a lightweight building block by any module needing to configure and call
an outbound webservice, without pulling in extra frameworks.

