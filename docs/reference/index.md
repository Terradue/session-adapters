# Reference

Reference pages describe the library's current interfaces and behavior.

| Topic | Contents |
| --- | --- |
| [URL schemes](url-schemes.md) | Accepted forms for HTTP, file, S3, and OCI URLs |
| [Methods and responses](methods-and-responses.md) | Dispatch, status codes, common headers, and errors |
| [`BearerAuthHTTPAdapter`](bearer-auth-http-adapter.md) | Bearer-header injection |
| [`FileAdapter`](file-adapter.md) | Local path operations |
| [`S3Adapter`](s3-adapter.md) | Constructor, query parameters, header mapping, listings |
| [`OCIAdapter`](oci-adapter.md) | References, authentication, and ORAS operations |
| [Current limitations](limitations.md) | Known behavioral constraints |

Names beginning with an underscore and the helper types in `base.py` and
`http_conts.py` are internal implementation details and are not part of the
documented public API.
