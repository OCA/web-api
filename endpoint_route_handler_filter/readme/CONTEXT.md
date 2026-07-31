Odoo serves all registered controllers — standard web controllers as
well as any FastAPI endpoints mounted via `fastapi.endpoint` — through a
single WSGI application, regardless of which port (`http_port` /
longpolling port) a given worker process is listening on. There is no
built-in mechanism to say "these routes exist only on port X."

In practice this means that once a FastAPI endpoint is installed, it is
reachable from every process and every port Odoo happens to be running
on, including the main public-facing one. Restricting access to it then
falls entirely on network-level controls (reverse proxy IP allowlists,
firewall rules), which:

- protect the network path to the endpoint, but not the fact that the
  route exists on every process, and
- offer no protection against a request that legitimately originates
  from an allowed network (e.g. a compromised internal host).

For internal, technical, or automation-only endpoints — where the goal
is to expose a narrow set of actions to internal systems without
enlarging the attack surface of the main public Odoo instance — it is
preferable that the routes simply do not exist on the public process at
all.

This module addresses that by making route registration conditional on
a process-local setting (not a database value, since `ir.config_parameter`
is shared across all processes and workers connected to the same
database and would not allow differentiating between them). This allows
a deployment pattern of two Odoo processes, same codebase and database,
started with different configuration:

- one process without the flag → internal routes never registered
  (public, e.g. port 8069),
- one process with the flag → internal routes registered (internal
  only, e.g. port 8070, restricted at the network layer to trusted
  sources).

Network-level restriction (firewall/reverse proxy) and endpoint-level
authentication (JWT/API key on the FastAPI app) remain necessary and are
complementary to this module, not replaced by it. This module removes
one layer of exposure (route existence on the public process); it does
not replace access control on the internal one.
