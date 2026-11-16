const API_BASE_URL = (
    import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

async function handle(response) {
    const data = await response.json().catch(() => null);

    if (!response.ok) {
        const detail = data && data.detail;
        let message = "Request failed with status " + response.status;

        if (typeof detail === "string") {
            message = detail;
        } else if (Array.isArray(detail)) {
            message = detail.map(item => item.msg || "Validation error").join("; ");
        }

        throw new Error(message);
    }

    return data;
}

function request(url, options) {
    return fetch(API_BASE_URL + url, options)
        .then(handle)
        .catch(error => {
            if (error instanceof TypeError) {
                throw new Error(
                    "Backend connection failed. Check API URL, internet connection and CORS settings."
                );
            }

            throw error;
        });
}

function qs(params) {
    const searchParams = new URLSearchParams();

    Object.keys(params || {}).forEach(key => {
        const value = params[key];

        if (value !== "" && value !== null && value !== undefined) {
            searchParams.append(key, value);
        }
    });

    return searchParams.toString();
}

export const api = {
    health: function() {
        return request("/health");
    },

    latest: function(source) {
        let url = "/api/latest";

        if (source) {
            url += "?source=" + encodeURIComponent(source);
        }

        return request(url);
    },

    history: function(params) {
        const query = qs(params || {});
        let url = "/api/history";

        if (query) {
            url += "?" + query;
        }

        return request(url);
    },

    post: function(body) {
        return request("/api/sensors", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(body)
        });
    },

    model: function() {
        return request("/api/model");
    }
};