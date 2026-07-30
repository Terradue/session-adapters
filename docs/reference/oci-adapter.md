# `OCIAdapter`

::: session_adapters.oci_adapter.OCIAdapter
    options:
      members:
        - __init__
        - close

## Constructor parameters

| Parameter | Purpose |
| --- | --- |
| `hostname` | Registry hostname used to construct and log out the ORAS client |
| `username` | Registry login username |
| `password` | Registry login password or token |
| `outdir` | Directory passed to ORAS when pulling |

Authentication is attempted only when `hostname`, `username`, and `password`
are all truthy. A failed login is logged and followed by an anonymous attempt.
A client is created for each operation.

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
