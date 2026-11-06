-- Drop the OAuth2 secrets of the webservice backends, so that a database
-- copied from another environment does not keep the production credentials.
UPDATE webservice_backend
   SET oauth2_clientid = NULL,
       oauth2_client_secret = NULL,
       oauth2_client_auth_value = NULL,
       oauth2_token = NULL;
