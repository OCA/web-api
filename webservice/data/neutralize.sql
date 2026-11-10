-- remove webservice backend OAuth2 credentials
-- (base credentials are cleared by webservice_core/data/neutralize.sql)
UPDATE webservice_backend
   SET oauth2_clientid = NULL,
       oauth2_client_secret = NULL,
       oauth2_client_auth_value = NULL,
       oauth2_token = NULL;
