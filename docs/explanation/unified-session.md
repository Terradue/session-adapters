# One session, several transports

Requests separates the user-facing session from the object that performs a
particular transport. `Session.mount(prefix, adapter)` registers that transport
for a family of URLs. When preparing a request, Requests selects the adapter
whose prefix is the longest match.

`session-adapters` uses this extension point to make storage resources behave
like HTTP resources:

```text
requests.Session
├── https://api.example/  → BearerAuthHTTPAdapter → HTTP service
├── file://               → FileAdapter           → local filesystem
├── s3://                 → S3Adapter             → boto3 S3 client
└── oci://                → OCIAdapter            → ORAS client
```

The benefit is interface consistency. Callers can prepare requests, set
headers, inspect status codes, and consume `Response` objects without choosing
a separate client abstraction at every call site. The URL communicates where
the resource lives.

The abstraction does not make the backends identical. Filesystems, object
stores, registries, and HTTP servers have different semantics:

- S3 has object versions, ranges, prefixes, and service-side encryption.
- OCI distinguishes tags from content digests and may materialize artifacts
  into an output directory.
- A filesystem can recursively delete a directory, while S3 deletes one key.
- HTTP authentication is a header, AWS uses a credential provider chain, and
  OCI uses a registry login.

For that reason, the library preserves a common Requests-shaped surface while
exposing backend-specific configuration through constructors, headers, and
query parameters.

## Mount scope is policy

Adapter selection also establishes a security boundary. A broad
`session.mount("https://", bearer_adapter)` mount sends the bearer token to
every HTTPS host accessed by that session. A host- or path-specific prefix
limits that authority.

Likewise, mounting `FileAdapter` makes local file operations available to any
code that receives the session. The mount should therefore be treated as a
capability granted to that code, especially when request URLs can originate
from untrusted input.
