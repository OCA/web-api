## Calling an Endpoint

Send a POST request with a JSON body to the endpoint's route. The example below
uses Bearer authentication with an API key:

```bash
curl -X POST https://your-odoo.com/json2/contacts/get_partners \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{"domain": [["is_company", "=", true]], "limit": 10}'
```

## API Documentation

Auto-generated documentation for all JSON-2 endpoints is available at
`/json2/doc`, grouped by route group. Each endpoint's visibility respects the
**Allowed Groups** setting — users only see endpoints they have access to.
Filter by route group with `/json2/doc/{route_group}`.
