-- remove webservice backend credentials
UPDATE webservice_backend
   SET username = NULL,
       password = NULL,
       api_key = NULL;
