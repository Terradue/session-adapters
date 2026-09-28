# Work with OCI artifacts

Mount an anonymous adapter when the registry permits unauthenticated access:

```python
import requests

from session_adapters.oci_adapter import OCIAdapter

session = requests.Session()
session.mount("oci://", OCIAdapter(outdir="/tmp/oci-artifacts"))
```

## Authenticate to a registry

Starting with **0.6.0**, `OCIAdapter` accepts a `ContainersAuth` model instead
of the `hostname`, `username`, and `password` constructor arguments. Migrate
existing calls using the `ContainersAuth.add_auth` method (available since **0.7.0**):

```python
import os

from session_adapters.conainers_auth import ContainersAuth

hostname = "registry.example.com"
username = os.environ["OCI_USERNAME"]
password = os.environ["OCI_PASSWORD"]
containers_auth = ContainersAuth()
containers_auth.add_auth(hostname, username, password)
adapter = OCIAdapter(
    containers_auth=containers_auth,
    outdir="/tmp/oci-artifacts",
)
session.mount("oci://", adapter)
```

The import path is `session_adapters.conainers_auth` (the module's current spelling).
`ContainersAuth.add_auth` updates the model in place and returns `None`. It creates
`auths` if needed and replaces any entry for the supplied key, preserving other
entries and helpers. Call it before constructing the adapter, which snapshots
the configuration. The helper Base64-encodes `username:password`; Base64 is
encoding, not encryption.

The adapter serializes the model for Docker's `load_auth_config` using
`model_dump(mode="json", by_alias=True, exclude_none=True)`. The resulting
structure is:

```json
{
  "auths": {
    "registry.example.com": {
      "auth": "<base64-encoded username:password>"
    }
  }
}
```

`by_alias=True` preserves names such as `credHelpers`. `exclude_none=True`
omits unset fields, including `identitytoken`; Docker's parser would otherwise
prioritize that field over `auth` even when its value is null.

### Scope credentials to a namespace or repository

Use a namespace or repository as the `auths` key to restrict credential matching:

```python
containers_auth = ContainersAuth()
containers_auth.add_auth("registry.example.com/team/project", username, password)
session.mount("oci://", OCIAdapter(containers_auth=containers_auth))
```

For `oci://registry.example.com/team/project:latest`, the adapter checks
`registry.example.com/team/project`, then `registry.example.com/team`, then
`registry.example.com`. The first matching entry wins. Sibling namespaces
never inherit each other's credentials. One configuration can contain entries
for multiple registries and namespaces.

### Use a credential helper

Configure a helper by registry hostname, including the port when applicable:

```python
containers_auth = ContainersAuth(
    cred_helpers={"registry.example.com": "pass"},
)
session.mount("oci://", OCIAdapter(containers_auth=containers_auth))
```

This uses `docker-credential-pass` through `docker.credentials.Store`. A helper
is queried for the registry, not the repository path. Helper credentials take
precedence over inline credentials; if the helper reports no credentials,
the adapter falls back to the matching inline entry.

A client is created for each operation. Login is attempted only when the
resolved credentials contain both a nonempty username and password. Missing
credentials, credential resolution errors, or a failed login handshake lead
to an anonymous client. An `identitytoken`-only entry does not trigger login.
After the operation, the adapter attempts to log out all hosts known to the
client and closes its HTTP session.

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
