-- Drop the endpoints and credentials of the webservice backends, so that
-- a database copied from another environment does not call external services.
-- `url` is required, so it gets a placeholder instead of NULL.
UPDATE webservice_backend
   SET url = 'https://neutralized.invalid',
       username = NULL,
       password = NULL,
       api_key = NULL;
