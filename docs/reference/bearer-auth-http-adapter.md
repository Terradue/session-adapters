# `BearerAuthHTTPAdapter`

::: session_adapters.bearer_auth_http_adapter.BearerAuthHTTPAdapter
    options:
      members:
        - __init__
        - send

## Behavior

- Inherits Requests' `HTTPAdapter`.
- Stores the constructor's token as `adapter.token`.
- Sets `Authorization` immediately before delegating the request.
- Uses the exact value `Bearer {token}`.
- Replaces an existing `Authorization` request header.
- Preserves the positional and keyword arguments supplied to `send`.

The adapter does not refresh tokens, obtain credentials, redact logs, or limit
the destinations to which a token is sent. Destination scope is controlled by
the prefix used with `Session.mount`.
