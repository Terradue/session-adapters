# Methods and responses

## Method matrix

| Adapter | `GET` | `HEAD` | `PUT` | `DELETE` |
| --- | --- | --- | --- | --- |
| Bearer HTTP | Delegated to Requests | Delegated | Delegated | Delegated |
| File | Read file | File metadata | Write text | Remove path |
| S3 | Get object or list prefix | Head object | Put object | Delete object |
| OCI | Pull first result | Look up manifest | Push bytes | Delete reference |

The non-HTTP adapters dispatch `GET`, `HEAD`, `PUT`, and `DELETE`. Another
valid HTTP method returns `405 Method Not Allowed` with:

```http
Allow: GET, HEAD, PUT, DELETE
```

## Common response behavior

The file, S3, and OCI adapters return a `requests.Response` subclass and set
its `url` and `request` attributes. They add a `Date` header before dispatch.

File and OCI downloads use `response.raw` for streaming. S3 object downloads
wrap boto3's streaming body. Prefix listings instead place a JSON document in
`response.content`.

## Common exception mapping

Exceptions escaping an adapter operation are mapped by the shared dispatcher:

| Exception | Response |
| --- | --- |
| `TypeError` | `400 Bad Request` |
| `ValueError` | `405 Method Not Allowed` |
| Other `Exception` | `500 Internal Server Error` |

The error message is returned as UTF-8 plain text with `Content-Type` and
`Content-Length` headers. Individual adapters can intercept an exception and
return a more specific result; for example, OCI maps an authorization-related
`ValueError` during pull to `401 Unauthorized`.

!!! note

    These mappings describe current implementation behavior. A `ValueError`
    can originate in backend processing as well as method parsing, so `405`
    does not always mean that the caller selected an unsupported method.
