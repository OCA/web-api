-- remove webservice backend credentials
UPDATE webservice_backend
   SET username = NULL,
       password = NULL,
       api_key = NULL,
       oauth2_clientid = NULL,
       oauth2_client_secret = NULL,
       oauth2_client_auth_value = NULL,
       oauth2_token = NULL;
