# session-adapters

[![PyPI - Version](https://img.shields.io/pypi/v/session-adapters.svg)](https://pypi.org/project/session-adapters)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/session-adapters.svg)](https://pypi.org/project/session-adapters)

Requests transport adapters for bearer-authenticated `http(s)://`, `file://`,
`s3://`, and `oci://` URLs.

**[Read the documentation](https://terradue.github.io/session-adapters/)**

## Why This Project

`session-adapters` lets you use a standard `requests.Session` with authenticated
HTTP requests and non-HTTP backends:

- `http://` and `https://` with bearer token authentication
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

from session_adapters.bearer_auth_http_adapter import BearerAuthHTTPAdapter
from session_adapters.file_adapter import FileAdapter
from session_adapters.oci_adapter import OCIAdapter
from session_adapters.s3_adapter import S3Adapter

session = requests.Session()
session.mount("https://", BearerAuthHTTPAdapter("my-token"))
session.mount("file://", FileAdapter())
session.mount("s3://", S3Adapter())
session.mount("oci://", OCIAdapter())

# Bearer-authenticated HTTPS request
resp = session.get("https://api.example.com/resource")
print(resp.status_code)

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

### Bearer Auth HTTP Adapter

- Adds an `Authorization: Bearer <token>` header to every request it handles
- Replaces an existing `Authorization` header
- Can be mounted on a specific URL prefix to limit where the token is sent
- Mount separate adapters for `http://` and `https://` if both schemes are needed

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

Preview the documentation:

```bash
hatch run docs:serve
```

Build the documentation with strict validation:

```bash
hatch run docs:build
```

## License

## License

[![Apache License, Version 2.0](https://img.shields.io/badge/license-Apache%20License%202.0-blue)](https://www.apache.org/licenses/LICENSE-2.0)
