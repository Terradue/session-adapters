# Authentication models

The adapters deliberately follow the credential model native to each backend.
There is no shared `session-adapters` credential store.

## Bearer-authenticated HTTP

`BearerAuthHTTPAdapter` holds one token and replaces the outgoing
`Authorization` header. The mount prefix determines where it applies.
Rotation, refresh, and secret retrieval remain application responsibilities.

This model is request-oriented: the credential is sent as part of each HTTP
request.

## S3

`S3Adapter` creates a boto3 client. Explicit constructor credentials override
the need for discovery, but the usual boto3 provider chain is generally more
appropriate for production:

- environment variables;
- shared AWS configuration and credential files;
- workload or instance roles;
- other botocore-supported providers.

This model is client-oriented: botocore resolves credentials and signs each
backend request.

## OCI registries

`OCIAdapter` optionally receives a hostname, username, and password. When all
are present, each operation creates a hostname-specific ORAS client and calls
its login method. The adapter logs out after the operation.

If login raises an exception, the adapter logs a warning and retries with an
anonymous client. This is useful for registries containing both public and
private content, but applications that require strict authenticated-only
access should account for that fallback.

## Why the differences remain visible

Trying to force these models into one generic token would discard useful
backend behavior. AWS credentials can be short-lived and automatically
resolved; OCI needs a registry context; bearer tokens depend on URL scope.
Keeping authentication in each adapter makes those differences explicit and
allows the underlying clients to perform their native protocol work.
