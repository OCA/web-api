# Copyright 2026 Camptocamp SA
# @author: Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import functools

from odoo import models

from odoo.addons.openapi_doc_base.sources import DocSource

NO_GROUP = "default"


class IrHttp(models.AbstractModel):
    """One docs source per endpoint model and route group."""

    _inherit = "ir.http"

    def _openapi_endpoint_models(self):
        """Concrete models using `endpoint.mixin` (eg: `edi.endpoint`)."""
        names = self.env.registry.descendants(["endpoint.mixin"], "_inherit")
        return [n for n in sorted(names) if not self.env[n]._abstract]

    def _openapi_doc_sources(self):
        """Add a source per model (category) and route group (app)."""
        sources = super()._openapi_doc_sources()
        for model_name in self._openapi_endpoint_models():
            model = self.env[model_name].sudo()
            groups = model.search(model._openapi_documented_domain()).mapped(
                lambda r: r.route_group or NO_GROUP
            )
            for group in sorted(set(groups)):
                sources.append(
                    DocSource(
                        key=f"{model_name}.{group}",
                        title=f"{model._description}: {group}",
                        build=functools.partial(
                            self._openapi_build_endpoint_doc, model_name, group
                        ),
                        category=model_name,
                        app=group,
                    )
                )
        return sources

    def _openapi_build_endpoint_doc(self, model_name, group, env):
        """Build the document of the endpoints of a model and route group."""
        model = env[model_name].sudo()
        domain = model._openapi_documented_domain()
        if group == NO_GROUP:
            domain.append(("route_group", "in", (False, "")))
        else:
            domain.append(("route_group", "=", group))
        records = model.search(domain, order="route")
        return records._openapi_build_doc(title=f"{model._description}: {group}")

    def _openapi_doc_category_label(self, category):
        """Show the description of endpoint models (eg: `Endpoint`)."""
        if category in self._openapi_endpoint_models():
            return self.env[category]._description
        return super()._openapi_doc_category_label(category)

    def _openapi_security_scheme(self, auth):
        """Endpoints use `user_endpoint` for session based auth."""
        if auth == "user_endpoint":
            auth = "user"
        return super()._openapi_security_scheme(auth)
