# Build your first multi-backend session

In this tutorial, you will mount two adapters on one `requests.Session`, write
and read a local resource, and prepare the same session for authenticated HTTP
requests. No network request is made.

## Install the package

Create and activate a virtual environment, then install `session-adapters`:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install session-adapters
```

On Windows PowerShell, activate the environment with
`.venv\Scripts\Activate.ps1`.

## Create the session

Create `first_session.py`:

```python
import tempfile
from pathlib import Path

import requests

from session_adapters.bearer_auth_http_adapter import BearerAuthHTTPAdapter
from session_adapters.file_adapter import FileAdapter

session = requests.Session()
session.mount("file://", FileAdapter())
session.mount(
    "https://api.example.com/",
    BearerAuthHTTPAdapter("tutorial-token"),
)
```

Each mount associates a URL prefix with an adapter. A request to a `file://`
URL is handled locally; a matching HTTPS request is delegated to Requests
after the bearer header is attached.

## Write a local resource

Continue the script:

```python
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "message.txt"
    url = path.as_uri()

    put_response = session.put(url, data="hello from session-adapters")
    print("created:", path.exists())
```

`Path.as_uri()` produces the correct absolute `file://` URL for the current
platform. The adapter creates missing parent directories.

!!! note "Current `PUT` response"

    A successful local-file `PUT` currently leaves `status_code` unset. Check
    the target or follow with `HEAD` when confirmation is required. Do not call
    `raise_for_status()` on that `PUT` response.

## Inspect and read it

Still inside the temporary-directory block, add:

```python
    head_response = session.head(url)
    print("head:", head_response.status_code)
    print("type:", head_response.headers.get("Content-Type"))

    get_response = session.get(url)
    print("get:", get_response.status_code)
    print("body:", get_response.text)
```

The adapter exposes the file as a Requests response. `HEAD` returns metadata;
`GET` supplies a binary stream that Requests makes available through
`response.raw`, `response.content`, and `response.text`.

## Delete it

Finish the block:

```python
    delete_response = session.delete(url)
    print("delete:", delete_response.status_code)
    print("still exists:", path.exists())
```

Run the script:

```bash
python first_session.py
```

You should see output similar to:

```text
created: True
head: 200
type: text/plain
get: 200
body: hello from session-adapters
delete: 200
still exists: False
```

## What you built

The same session now knows how to route both local and selected HTTPS URLs.
You did not need a separate storage-client interface for the local resource.
The HTTP mount is deliberately host-specific, preventing the tutorial token
from being attached to unrelated HTTPS requests.

Next, choose a backend-specific guide:

- [Add bearer authentication](../how-to/bearer-auth.md)
- [Read and write S3 objects](../how-to/s3.md)
- [Work with OCI artifacts](../how-to/oci.md)
