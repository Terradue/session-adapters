# `OCIAdapter`

::: session_adapters.oci_adapter.OCIAdapter
    options:
      members:
        - __init__
        - close

## Constructor parameters

| Parameter | Purpose |
| --- | --- |
| `containers_auth` | Optional `ContainersAuth` model; defaults to an empty configuration |
| `outdir` | Directory passed to ORAS when pulling |

**Breaking change in 0.6.0:** `hostname`, `username`, and `password` are no
longer constructor parameters. See the [migration example](../how-to/oci.md#authenticate-to-a-registry).
The registry hostname now comes from each request URL.

## Adding inline credentials

```python
from session_adapters.conainers_auth import ContainersAuth

containers_auth = ContainersAuth()
containers_auth.add_auth(hostname, username, password)
```

Since 0.7.0, call this method on an existing `ContainersAuth` model with three strings.
It updates the model in place and returns `None`, initializing `auths` when absent.
It stores an `Auth` entry containing the Base64-encoded UTF-8 `username:password`,
replacing the entry at `hostname` while preserving other entries and helpers.
The key can include a port or namespace/repository path. Populate the model
before constructing an adapter; later changes do not update existing adapters.

## Credential resolution

`ContainersAuth` and its inline `Auth` entries are defined in
`session_adapters.conainers_auth`.

- `auths` maps a registry, namespace, or repository to an `Auth` entry.
  Its `auth` field contains the Base64-encoded UTF-8 string `username:password`.
- Inline lookup checks the full repository first, then each parent namespace,
  then the registry. Tags and digests are excluded. The first matching entry
  is selected, even if it has no usable username/password pair.
- URL-shaped keys are parsed to remove their scheme, preserving the host,
  port, and namespace path. Trailing slashes are removed. Bare `host:port`
  keys are preserved.
- Only the selected inline entry is passed to `AuthConfig.resolve_authconfig`,
  preventing Docker's hostname normalization from matching a sibling namespace.
- `cred_helpers` (serialized as `credHelpers`) maps registry hostnames to
  helper suffixes. Docker's `Store` executes the helper. Helper credentials
  take precedence; missing helper credentials fall back to the selected
  inline entry.

Login requires a nonempty username and password in the resolved credentials.
Identity-token-only entries do not trigger login. Missing credentials or
errors during resolution or login result in an anonymous client.

A client is created for each operation. Cleanup attempts logout for all
hosts known to the client and closes its HTTP session, including after
operation failures. A client whose login fails is cleaned up before the
anonymous fallback is created.

## Reference parsing

| URL | ORAS target |
| --- | --- |
| `oci://registry.example/repo` | `registry.example/repo` |
| `oci://registry.example/repo:v1` | `registry.example/repo:v1` |
| `oci://registry.example/team/repo@sha256:abc` | `registry.example/team/repo@sha256:abc` |

## Operation behavior

### `GET`

Calls `client.pull(target=ref, outdir=outdir)`.

- Empty results produce `404 Not Found`.
- The first returned path is inspected.
- A file produces `200 OK`, file metadata, and a raw response stream.
- A directory produces `501 Not Implemented`.
- A `ValueError` containing `Unauthorized` produces `401 Unauthorized`.

### `HEAD`

Uses `client.manifest(ref)` or `client.get_manifest(ref)` when present.
Otherwise it falls back to `client.pull(ref)`. A manifest dictionary may
populate media-type and `Docker-Content-Digest` response headers. Any exception
inside this operation produces `404 Not Found`.

### `PUT`

Calls `client.push(ref, data=body, media_type=media_type)`. If that signature
raises `TypeError`, it retries as `client.push(ref, body)`.

- The media type comes from `Accept`, defaulting to
  `application/octet-stream`.
- A string body is UTF-8 encoded.
- Success produces `201 Created`.
- A client without a compatible push method produces
  `503 Service Unavailable`.

### `DELETE`

Calls `client.delete(ref)` when available.

- Success produces `204 No Content`.
- A missing method produces `405 Method Not Allowed`.
- An exception from the delete call produces `502 Bad Gateway`.
