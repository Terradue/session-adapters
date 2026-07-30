# URL schemes

## HTTP and HTTPS

```text
https://host[:port]/path[?query]
http://host[:port]/path[?query]
```

`BearerAuthHTTPAdapter` does not alter URL parsing. It delegates transport to
Requests' `HTTPAdapter`.

Mounting is prefix-based. A mount on
`https://api.example.com/private/` applies only below that path, while a mount
on `https://` applies to every HTTPS URL in the session.

## Local files

```text
file:///absolute/path
file://localhost/absolute/path
```

The hostname must be empty or exactly `localhost`. Other hostname components
produce a `400 Bad Request` response. Percent-decoding is not performed by the
adapter after `urllib.parse.urlparse`; use `Path.as_uri()` and verify paths
containing escaped characters against your platform.

## S3

```text
s3://bucket/key
s3://bucket/prefix/
s3://bucket/
```

The hostname is the bucket. The path, without its leading slash, is the key.
An empty key or a key ending in `/` represents a prefix listing for `GET`.

Recognized query parameters depend on the operation:

```text
?range=bytes%3D0-99
?versionId=example-version
?delimiter=%2F&maxKeys=100
?sse=AES256
?sse=aws%3Akms&kmsKeyId=example-key-id
```

## OCI

```text
oci://registry/repository
oci://registry/repository:tag
oci://registry/repository@algorithm:digest
```

The hostname is the registry. The remainder is the repository plus an
optional reference:

- the final `@` separates a digest reference;
- otherwise, the final `:` separates a tag;
- if neither separator exists, the ORAS reference has no explicit tag or
  digest.

Repository paths may contain multiple segments. The registry and repository
are required. Query parameters are parsed but are not currently used by OCI
operations.
