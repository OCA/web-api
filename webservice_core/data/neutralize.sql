-- remove webservice backend and endpoint credentials
UPDATE webservice_backend
   SET username = NULL,
       password = NULL,
       api_key = NULL;
UPDATE webservice_endpoint
   SET username = NULL,
       password = NULL,
       api_key = NULL;
