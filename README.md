# session-adapters

[![PyPI - Version](https://img.shields.io/pypi/v/session-adapters.svg)](https://pypi.org/project/session-adapters)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/session-adapters.svg)](https://pypi.org/project/session-adapters)

Requests transport adapters for `file://`, `s3://`, and `oci://` URLs.

## Why This Project

`session-adapters` lets you use a standard `requests.Session` with non-HTTP backends:

- `file://` for local filesystem artifacts
- `s3://` for AWS S3 objects and prefix listings
- `oci://` for OCI registry artifacts (via ORAS client)

This keeps one client interface while changing only the URL scheme.

## Installation

```bash
pip install session-adapters
```

## Quick Start

```python
import requests

from session_adapters.file_adapter import FileAdapter
from session_adapters.s3_adapter import S3Adapter
from session_adapters.oci_adapter import OCIAdapter

session = requests.Session()
session.mount("file://", FileAdapter())
session.mount("s3://", S3Adapter())
session.mount("oci://", OCIAdapter())

# Local file
resp = session.get("file:///tmp/example.txt")
print(resp.status_code)

# S3 object
resp = session.get("s3://my-bucket/path/to/object.json")
print(resp.status_code)

# OCI artifact
resp = session.get("oci://registry.example.com/my-repo:latest")
print(resp.status_code)
```

## Adapter Notes

### File Adapter

- Supports `GET`, `HEAD`, `PUT`, `DELETE`
- Uses local filesystem paths from `file://` URLs

### S3 Adapter

- Supports `GET`, `HEAD`, `PUT`, `DELETE`
- Supports query options like:
  - `range=bytes=0-99`
  - `versionId=...`
  - `delimiter=/`
  - `maxKeys=...`

### OCI Adapter

- Supports `GET`, `HEAD`, `PUT`, `DELETE`
- Parses refs as tags (`:tag`) or digests (`@sha256:...`)
- Uses `oras.client.OrasClient` under the hood

## Development

Run tests:

```bash
hatch run test:test-q
```

Run lint checks:

```bash
hatch run dev:check
ruff format --check .
```

## License

`session-adapters` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
