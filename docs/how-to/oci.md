# Work with OCI artifacts

Mount an anonymous adapter when the registry permits unauthenticated access:

```python
import requests

from session_adapters.oci_adapter import OCIAdapter

session = requests.Session()
session.mount("oci://", OCIAdapter(outdir="/tmp/oci-artifacts"))
```

## Authenticate to a registry

All three authentication values must be supplied:

```python
import os

adapter = OCIAdapter(
    hostname="registry.example.com",
    username=os.environ["OCI_USERNAME"],
    password=os.environ["OCI_PASSWORD"],
    outdir="/tmp/oci-artifacts",
)
session.mount("oci://", adapter)
```

The adapter creates an ORAS client per operation, logs in, performs the
operation, and logs out. If the login handshake fails, it retries with an
anonymous client.

## Pull by tag or digest

```python
by_tag = session.get(
    "oci://registry.example.com/example/project:latest",
    stream=True,
)

by_digest = session.get(
    "oci://registry.example.com/example/project@sha256:0123456789abcdef",
    stream=True,
)
```

ORAS downloads into `outdir`. When the result identifies a file, the response
streams the first returned file.

## Push an artifact

The adapter currently takes the media type from the `Accept` header:

```python
response = session.put(
    "oci://registry.example.com/example/project:v1",
    data=b"artifact bytes",
    headers={"Accept": "application/octet-stream"},
)
response.raise_for_status()
```

If no `Accept` header is present, it uses `application/octet-stream`.

## Inspect or delete a reference

```python
metadata = session.head(
    "oci://registry.example.com/example/project:v1"
)

deleted = session.delete(
    "oci://registry.example.com/example/project:v1"
)
```

`HEAD` uses a manifest method when the installed ORAS client exposes one and
otherwise falls back to a pull. `DELETE` requires a compatible `delete`
method. Consult [Current limitations](../reference/limitations.md) before
depending on OCI behavior across ORAS releases.
