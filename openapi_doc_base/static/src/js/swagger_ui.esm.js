/* Copyright 2026 Camptocamp SA
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl). */
/* global window, document, SwaggerUIBundle, SwaggerUIStandalonePreset, URL */

const SERVER_STORAGE_KEY = "openapi_doc_base.server";

/**
 * Setup the server selector: the URL of the page is the default.
 *
 * @returns {HTMLSelectElement|null} the selector
 */
function setupServerSelector() {
    const select = document.getElementById("o_openapi_server");
    if (!select) {
        return null;
    }
    const origin = window.location.origin;
    select.querySelector(".o_openapi_server_page").textContent =
        `Current domain: ${origin}`;
    // Same as the page: no need to propose it twice
    for (const option of [...select.options]) {
        if (option.value === origin) {
            option.remove();
        }
    }
    let stored = "";
    try {
        stored = window.localStorage.getItem(SERVER_STORAGE_KEY) || "";
    } catch {
        // Storage not available: keep the default
    }
    if ([...select.options].some((option) => option.value === stored)) {
        select.value = stored;
    }
    select.addEventListener("change", () => {
        try {
            window.localStorage.setItem(SERVER_STORAGE_KEY, select.value);
        } catch {
            // Storage not available: the choice lasts until reload
        }
    });
    return select;
}

/**
 * Point requests (and curl snippets) to the selected server.
 *
 * @param {HTMLSelectElement|null} select the server selector
 * @returns {Function} a Swagger UI request interceptor
 */
function serverInterceptor(select) {
    return (req) => {
        const base = select && select.value;
        // Keep requests loading the documents on the page origin
        if (base && !req.loadSpec) {
            const url = new URL(req.url, window.location.href);
            req.url = base + url.pathname + url.search;
        }
        return req;
    };
}

window.addEventListener("load", function () {
    const node = document.getElementById("swagger-ui");
    const settings = JSON.parse(node.dataset.settings || "{}");
    const select = setupServerSelector();
    window.ui = SwaggerUIBundle(
        Object.assign(
            {
                dom_id: "#swagger-ui",
                deepLinking: true,
                presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
                plugins: [SwaggerUIBundle.plugins.DownloadUrl],
                layout: "StandaloneLayout",
                requestInterceptor: serverInterceptor(select),
            },
            settings
        )
    );
});
