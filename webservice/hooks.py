# Copyright 2025 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.server_environment.uninstall import restore_env_managed_columns

ENV_MANAGED_FIELDS = [
    "protocol",
    "url",
    "auth_type",
    "username",
    "password",
    "api_key",
    "api_key_header",
    "content_type",
    "oauth2_flow",
    "oauth2_scope",
    "oauth2_clientid",
    "oauth2_client_secret",
    "oauth2_authorization_url",
    "oauth2_token_url",
    "oauth2_audience",
]


def post_init_hook(env):
    env["webservice.backend"]._preserve_not_env_managed_data(ENV_MANAGED_FIELDS)


def uninstall_hook(env):
    """Restore database columns dropped by server.env.mixin."""
    restore_env_managed_columns(
        env,
        "webservice.backend",
        ENV_MANAGED_FIELDS,
    )
