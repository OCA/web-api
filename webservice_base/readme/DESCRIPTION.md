This module creates WebService frameworks to be used globally.

It introduces support for HTTP Request protocol.
The webservice HTTP call returns by default the content of the response.
A context 'content_only' can be passed to get the full response object.

It comes with no additional dependencies.
To rely also on the `components` objetcs, see the `webservid` addon odule instead.
This work is derived from that module,
removing the `components` and `server_env` dependencies to make it lighter.
