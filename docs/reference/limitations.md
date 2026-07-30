# Current limitations

This page records constraints of the current implementation so that examples
and integrations can account for them.

## Shared behavior

- The shared dispatcher maps every escaping `ValueError` to `405 Method Not
  Allowed`, even when the value error is unrelated to an HTTP method.
- Error response bodies can expose backend exception text. Treat them as
  diagnostic data and avoid returning them directly across a trust boundary.
- Only `GET`, `HEAD`, `PUT`, and `DELETE` are dispatched for the non-HTTP
  adapters.

## Local files

- Successful `PUT` does not assign a status code.
- `PUT` opens the destination in text mode. Use a string request body; arbitrary
  binary bodies are not supported reliably.
- `GET` does not list directories.
- `DELETE` recursively removes directories, suppresses removal errors, and
  returns the status determined before deletion.
- URL paths are not explicitly percent-decoded after parsing.

## S3

- Prefix listings expose no continuation-token input or output, although
  `IsTruncated` is returned.
- Only a subset of boto3 request headers and options is mapped.
- Repeated query parameters use their first value.
- Backend exceptions rely on the shared exception mapping rather than a
  complete translation of botocore errors to HTTP responses.

## OCI

- Behavior depends on the methods and signatures exposed by the installed
  `oras` client.
- A pull response exposes only the first path returned by ORAS.
- Pulled directories are not listed.
- `HEAD` can fall back to a pull and maps every operation error to `404`.
- Parsed query parameters are currently unused.
- `PUT` uses the `Accept` request header as the artifact media type.
- Authentication failures fall back to anonymous access.
