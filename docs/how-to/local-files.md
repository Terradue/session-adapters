# Work with local files

Mount the adapter and use absolute file URLs:

```python
import requests

from session_adapters.file_adapter import FileAdapter

session = requests.Session()
session.mount("file://", FileAdapter())
```

## Read a file

```python
from pathlib import Path

path = Path("/tmp/report.json")
response = session.get(path.as_uri())

if response.ok:
    report = response.json()
```

Large responses are exposed through `response.raw`. Use streaming reads when
you do not want Requests to materialize the entire file:

```python
response = session.get(path.as_uri(), stream=True)
with response:
    for chunk in response.iter_content(chunk_size=64 * 1024):
        if chunk:
            process(chunk)
```

## Inspect metadata

```python
response = session.head(path.as_uri())
print(response.status_code)
print(response.headers.get("Last-Modified"))
print(response.headers.get("Content-Type"))
```

MIME types are inferred from the file extension with Python's `mimetypes`
module.

## Write text

```python
target = Path("/tmp/session-adapters/output.txt")
response = session.put(target.as_uri(), data="generated content")
```

Missing parent directories are created. The current implementation writes in
text mode and does not set a success status; see
[Current limitations](../reference/limitations.md).

## Delete a path

```python
response = session.delete(target.as_uri())
```

Deleting a directory is recursive.

!!! danger "The URL grants filesystem authority"

    `FileAdapter` performs operations with the permissions of the Python
    process. Validate user-supplied paths before issuing `PUT` or `DELETE`
    requests. A `DELETE` request can remove a non-empty directory tree.
