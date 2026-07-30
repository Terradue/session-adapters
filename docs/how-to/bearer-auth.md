# Add bearer authentication

Mount `BearerAuthHTTPAdapter` on the narrowest URL prefix that should receive
the token:

```python
import os

import requests

from session_adapters.bearer_auth_http_adapter import BearerAuthHTTPAdapter

session = requests.Session()
session.mount(
    "https://api.example.com/v1/",
    BearerAuthHTTPAdapter(os.environ["EXAMPLE_API_TOKEN"]),
)

response = session.get("https://api.example.com/v1/resources")
response.raise_for_status()
```

The adapter sets:

```http
Authorization: Bearer <token>
```

It replaces an `Authorization` header already present on the request.

## Cover HTTP and HTTPS

Requests treats the schemes as different prefixes. Mount an adapter for each
one only when the service genuinely uses both:

```python
token = os.environ["EXAMPLE_API_TOKEN"]
session.mount("https://api.example.com/", BearerAuthHTTPAdapter(token))
session.mount("http://api.example.com/", BearerAuthHTTPAdapter(token))
```

!!! danger "Avoid broad bearer mounts"

    Mounting on `"https://"` sends the token to every HTTPS destination handled
    by that session. Prefer a hostname or path prefix and never commit tokens
    to source control.

The adapter inherits Requests' normal proxy, TLS verification, certificate,
retry, and connection-pool behavior because it extends `HTTPAdapter`.
