# Response and error mapping

The central design goal is that callers receive a `requests.Response` no
matter which backend handles the URL. This requires translating backend output
into familiar HTTP-shaped fields.

## Metadata

The non-HTTP adapters create an extended response, attach the prepared request
and URL, and add a `Date` header.

The file adapter constructs metadata from `Path.stat()` and `mimetypes`. The S3
adapter copies the backend's response headers. The OCI adapter derives file
metadata after a pull and can obtain selected manifest metadata for `HEAD`.

## Content

There are two response paths:

- Streaming responses assign a file-like object to `response.raw`. This is
  used for files, pulled OCI artifacts, and S3 objects.
- Generated responses assign bytes to `response._content`. This is used for
  S3 prefix-listing JSON and plain-text error messages.

The distinction matters for resource ownership. Download responses own their
raw streams, so consuming them in a `with response:` block provides predictable
cleanup.

## Status codes are translations

For HTTP, the origin server provides the status. For the other backends, the
adapter chooses or copies one:

- local-file existence and metadata become `200` or `404`;
- boto3 operation metadata supplies S3 statuses;
- OCI pull, push, and delete outcomes become statuses such as `200`, `201`,
  and `204`;
- Python exceptions are translated by either the individual adapter or the
  shared dispatcher.

These translations make ordinary Requests checks convenient, but they do not
form a lossless model of every backend error. The
[methods and responses reference](../reference/methods-and-responses.md)
documents the exact current mappings.
