This module logs the requests and responses of endpoints (`endpoint.endpoint`) in
the database, using the generic `api.log` model of `api_log`.

Each log stores the request URL, method, headers, body and date, the response status,
headers and body, the elapsed time and, when the call failed, the stack trace. Logs are
written with a separate database connection, so the logs of failed calls are kept even
though the call's own transaction is rolled back.
