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

Since 0.6.0, `OCIAdapter` receives an optional `ContainersAuth` model. The
request URL supplies the registry and repository context. Inline credentials
are matched from the repository through its parent namespaces to the registry,
so a single adapter can serve multiple registries without sharing credentials
between sibling namespaces. Registry credential helpers are resolved through
Docker's credential store support and take precedence over inline entries.

Each operation creates an ORAS client. Login requires both a username and
password from the contextual configuration. Cleanup attempts logout for every
host known to that client and closes its HTTP session.

If credentials are missing, or resolution or login raises an exception, the
adapter uses an anonymous client. This is useful for registries containing
both public and private content, but applications that require strict
authenticated-only access should account for that fallback. See the
[OCI authentication guide](../how-to/oci.md#authenticate-to-a-registry) for
migration from the removed constructor arguments.

## Why the differences remain visible

Trying to force these models into one generic token would discard useful
backend behavior. AWS credentials can be short-lived and automatically
resolved; OCI needs a registry context; bearer tokens depend on URL scope.
Keeping authentication in each adapter makes those differences explicit and
allows the underlying clients to perform their native protocol work.
