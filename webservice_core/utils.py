# Copyright 2023 Camptocamp SA
# @author Simone Orsi <simahawk@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from requests.auth import AuthBase


class StaticHeaderAuth(AuthBase):
    """Requests auth handler injecting a static header into the request.

    Useful to authenticate against endpoints expecting the credentials in a
    non-standard Authorization header (e.g. ``Authorization: SSWS <token>``).
    Passing it as ``auth`` (rather than via ``headers``) also prevents
    requests-oauthlib from auto-generating an HTTP Basic ``Authorization``
    header out of the client id, which would otherwise override ours.
    """

    def __init__(self, header, value):
        self._header = header
        self._value = value

    def __call__(self, request):
        request.headers[self._header] = self._value
        return request


DEFAULT_BLACKLISTED_KEYS = ("apikey", "password", "pwd")


def is_blacklisted_key(key, blacklisted_keys=None):
    """Tell if a key looks sensitive, comparing case insensitively."""
    blacklisted_keys = blacklisted_keys or DEFAULT_BLACKLISTED_KEYS
    return any(bl_key.lower() in key.lower() for bl_key in blacklisted_keys)


def sanitize_url_for_log(url, blacklisted_keys=None):
    """Sanitize url to avoid loggin sensitive data"""
    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=False)
    clean_query = {
        k: v for k, v in query.items() if not is_blacklisted_key(k, blacklisted_keys)
    }
    parsed = parsed._replace(query=urlencode(clean_query, True))
    return urlunparse(parsed)


def sanitize_values_for_log(values, secret_keys=(), blacklisted_keys=None):
    """Return a copy of `values` (e.g. headers) safe to log.

    The values of the `secret_keys` and of the keys looking sensitive
    (see `is_blacklisted_key`) are masked. Keys are compared case
    insensitively.
    """
    secret_keys = {k.lower() for k in secret_keys}
    return {
        k: "***"
        if k.lower() in secret_keys or is_blacklisted_key(k, blacklisted_keys)
        else v
        for k, v in values.items()
    }
