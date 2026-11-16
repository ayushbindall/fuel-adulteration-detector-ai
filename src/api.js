async function handle(response) {
    var data = await response.json().catch(function() {
        return null;
    });

    if (!response.ok) {
        var detail = data && data.detail;
        var message = "Request failed with status " + response.status;

        if (typeof detail === "string") {
            message = detail;
        } else if (Array.isArray(detail)) {
            message = detail.map(function(item) {
                return item.msg || "Validation error";
            }).join("; ");
        }

        throw new Error(message);
    }

    return data;
}

function request(url, options) {
    return fetch(url, options).then(handle).catch(function(error) {
        if (error instanceof TypeError) {
            throw new Error(
                "Backend connection failed. Check whether FastAPI is running on port 8000."
            );
        }

        throw error;
    });
}

function qs(params) {
    var searchParams = new URLSearchParams();

    Object.keys(params || {}).forEach(function(key) {
        var value = params[key];

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
        var url = "/api/latest";

        if (source) {
            url += "?source=" + encodeURIComponent(source);
        }

        return request(url);
    },

    history: function(params) {
        var query = qs(params || {});
        var url = "/api/history";

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