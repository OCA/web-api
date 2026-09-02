-- remove webservice backend credentials stored as server environment defaults
-- (this module turns username/password/api_key/oauth2_clientid/oauth2_client_secret
-- into non-stored fields backed by the server_env_defaults JSON column
-- this neutralization is needed if both webservice and server_environment are installed,
-- so the plain columns nulled by webservice/data/neutralize.sql can be properly cleared)
UPDATE webservice_backend
   SET server_env_defaults = (
         server_env_defaults::jsonb
           - 'x_username_env_default'
           - 'x_password_env_default'
           - 'x_api_key_env_default'
           - 'x_oauth2_clientid_env_default'
           - 'x_oauth2_client_secret_env_default'
           - 'x_oauth2_client_auth_value_env_default'
       )::text
 WHERE server_env_defaults IS NOT NULL;
