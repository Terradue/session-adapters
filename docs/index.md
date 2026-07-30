# One session for HTTP, files, S3, and OCI

`session-adapters` extends [`requests.Session`][requests-session] with transport
adapters for:

- bearer-authenticated `http://` and `https://` resources;
- local `file://` paths;
- Amazon S3 and S3-compatible `s3://` object stores;
- OCI registry artifacts addressed with `oci://`.

The URL selects the backend. Your application keeps the familiar Requests
interface:

```python
import requests

from session_adapters.file_adapter import FileAdapter
from session_adapters.s3_adapter import S3Adapter

session = requests.Session()
session.mount("file://", FileAdapter())
session.mount("s3://", S3Adapter())

local = session.get("file:///tmp/config.yaml")
remote = session.get("s3://example-bucket/config.yaml")
```

## Choose what you need

<div class="grid cards" markdown>

-   :material-school: **Learn by doing**

    ---

    Create a session, mount adapters, and perform local operations in a
    self-contained walkthrough.

    [Start the tutorial](tutorials/first-session.md)

-   :material-list-box: **Complete a task**

    ---

    Configure authentication, use a specific backend, or connect to an
    S3-compatible service.

    [Browse how-to guides](how-to/index.md)

-   :material-book-open-variant: **Look something up**

    ---

    Find constructor parameters, URL formats, query options, methods, and
    response behavior.

    [Open the reference](reference/index.md)

-   :material-lightbulb-outline: **Understand the design**

    ---

    Learn how Requests chooses adapters and why each backend has a different
    authentication model.

    [Read the explanation](explanation/index.md)

</div>

## Installation

`session-adapters` requires Python 3.10 or newer:

```bash
python -m pip install session-adapters
```

The package installs the Requests, boto3, and ORAS dependencies required by
the adapters.

!!! warning "Backends still need configuration"

    Installing the package does not grant access to an HTTP service, S3
    account, or OCI registry. Configure credentials for each backend before
    using it. The local-file adapter can read and modify files accessible to
    the current process.

## A complete mounting example

```python
import requests

from session_adapters.bearer_auth_http_adapter import BearerAuthHTTPAdapter
from session_adapters.file_adapter import FileAdapter
from session_adapters.oci_adapter import OCIAdapter
from session_adapters.s3_adapter import S3Adapter

session = requests.Session()
session.mount(
    "https://api.example.com/",
    BearerAuthHTTPAdapter("replace-with-a-secret-token"),
)
session.mount("file://", FileAdapter())
session.mount("s3://", S3Adapter(region_name="eu-west-1"))
session.mount("oci://", OCIAdapter())
```

Mount bearer authentication on the narrowest useful URL prefix. Requests uses
the most specific matching prefix, and the adapter replaces any existing
`Authorization` header for matching requests.

[requests-session]: https://requests.readthedocs.io/en/stable/user/advanced/#session-objects
