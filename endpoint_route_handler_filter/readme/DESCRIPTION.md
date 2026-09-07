This module allows FastAPI-based endpoints (built on top of `fastapi` /
`OCA/rest-framework`) to be selectively registered depending on the Odoo
**process** that is running, instead of always being exposed on every worker
regardless of which port it listens on.

This makes it possible to run two (or more) Odoo processes against the
same database:

- a **public** process (e.g. port 8069) that never registers the
  internal endpoints, and
- an **internal** process (e.g. port 8070), reachable only from a
  trusted network (VPN, internal VLAN, firewall rule), that does
  register them.

The module does not implement any authentication, authorization, or
network restriction itself — that is left to the FastAPI endpoint's own
auth mechanism (API key, JWT, etc.) and to your reverse proxy / firewall
configuration. It only controls **route existence** per process.
