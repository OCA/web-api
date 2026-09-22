The module reads a single process-local setting to decide whether to
register the internal endpoint routes. It does **not** read this setting
from `ir.config_parameter`, since that table is shared by every process
and worker connected to the same database and would not allow two
processes to behave differently.

Choose **one** of the two mechanisms below, matching what the code
implements.

## Option A — Environment variable

Set ODOO_ENDPOINT_ROUTE_HANDLER_FILTER_GROUP for setting the allowed route groups.

Set ODOO_ENDPOINT_ROUTE_HANDLER_FILTER_IGNORE to ignore some route groups.

## Option B — Config file key

Add `odoo_endpoint_route_handler_ignore` and `odoo_endpoint_route_handler_filter` under `[options]` in the config file used to start the internal process only. 
Odoo's config loader accepts undeclared keys from the config file (it just won't accept them as CLI flags), so no changes to Odoo core are required.

```ini
; odoo_public.conf
[options]
http_port = 8069
odoo_endpoint_route_handler_ignore = internal,my_other_route ; internal and my_other_route are not accepted


; odoo_internal.conf
[options]
http_port = 8070
odoo_endpoint_route_handler_filter = internal,my_other_route ; Only internal and my_other_route are accepted
```

## Notes

- If you run the internal process with `--workers=N`, all N worker
  processes inherit the same setting — this is expected and desired.
- The setting only affects whether the routes are added to the routing
  map. It does not grant or restrict any permission by itself.
