# `FileAdapter`

::: session_adapters.file_adapter.FileAdapter
    options:
      members:
        - __init__
        - close

## Operation behavior

| Method | Behavior | Typical success status |
| --- | --- | --- |
| `GET` file | Sets metadata and streams the file | `200 OK` |
| `GET` directory | Directory listing is not implemented | `501 Not Implemented` |
| `HEAD` existing path | Sets modification time and inferred MIME type | `200 OK` |
| `PUT` | Creates parents and writes the request body in text mode | Unset |
| `DELETE` | Removes a file or recursively removes a directory | Status from the preceding `HEAD` |

For file responses:

- `Last-Modified` is formatted as an HTTP date;
- `Content-Type` is inferred from the path when possible;
- `GET` sets `Content-Length` to the file size;
- the response owns and closes the raw file stream.

Missing paths return `404 Not Found`. Filesystem permission errors observed by
`GET` or `HEAD` return `403 Forbidden`; other `OSError` values return
`400 Bad Request`.

## URL restrictions

Only URLs with no hostname or with the hostname `localhost` are accepted:

```text
file:///tmp/example.txt
file://localhost/tmp/example.txt
```

See [Current limitations](limitations.md) for text-mode writes, escaped paths,
and deletion behavior.
