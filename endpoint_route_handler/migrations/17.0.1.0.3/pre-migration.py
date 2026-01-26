from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, _version):
    # Remove redundant index on endpoint_route_handler_tool
    env.cr.execute("DROP INDEX IF EXISTS endpoint_route_handler_tool__route_index")
