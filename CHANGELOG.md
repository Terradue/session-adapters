# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Deprecated

### Removed

### Fixed

### Security

## [0.7.0] - 2026-09-29

### Added

- `ContainersAuth.get_instance(authfile)` to load and validate a registry
  authentication JSON file from a `Path`.

### Changed

- **Breaking:** Move `add_auth` from `session_adapters.oci_adapter` to
  `ContainersAuth.add_auth(hostname, username, password)`. Replace
  `add_auth(hostname, username, password, config)` with
  `config.add_auth(hostname, username, password)`.

### Fixed

- Update authentication tests and documentation for the relocated credential
  method, and correct authentication module formatting and import ordering.

## [0.6.0] - 2026-09-28

### Added

- `add_auth(hostname, username, password, containers_auth)` in
  `session_adapters.oci_adapter` to add or replace inline credentials in an existing configuration.

### Changed

- **Breaking:** `OCIAdapter` now accepts `containers_auth: ContainersAuth | None`
  instead of the `hostname`, `username`, and `password` constructor arguments.
  The registry is derived from each request. Migrate username/password pairs
  to Base64-encoded `Auth(auth=...)` entries inside `ContainersAuth(auths=...)`;
  see the [OCI migration guide](docs/how-to/oci.md#authenticate-to-a-registry).
- Resolve OCI inline credentials hierarchically by repository, namespace, and
  registry, without leaking credentials between sibling namespaces. Registry
  credential helpers use `docker.credentials.Store`. Anonymous fallback remains
  available when credentials are missing or authentication fails.
- Improved type annotations and internal code quality by addressing mypy,
  Ruff, and Bandit findings.

### Fixed

- OCI cleanup attempts logout for all hosts known to each client and closes its
  HTTP session, including clients discarded after a failed login.

## [0.5.0] - 2026-07-30

### Added

- gh-pages on github serves "text/yaml"
- MkDocs Material documentation site organized according to Diátaxis,
  with tutorials, how-to guides, reference, and explanation.

### Changed

- Stronger code chekers with Ruff+McCabe & Bandit

## [0.4.0] - 2026-07-15

### Added

- Add `BearerAuthHTTPAdapter` to attach a bearer token to HTTP requests.

## [0.3.0] - 2026-04-14

### Changed

- Replace `python-magic` MIME detection with the Python standard library's
  `mimetypes` module, removing the external `libmagic` runtime dependency.

### Fixed

- Fix file response MIME detection in environments where `libmagic` is not
  available or does not work.

## [0.2.0] - 2026-03-23

### Changed

- Create an OCI client for each request and log out after the request completes.
- Retry OCI operations anonymously when the authenticated login or handshake is
  rejected.

## [0.1.0] - 2026-03-06

### Added

- Add `requests` transport adapters for local files, Amazon S3 objects, and OCI
  registry artifacts.
- Support `GET`, `HEAD`, `PUT`, and `DELETE` operations across the adapters.
- Support S3 range, object version, delimiter, and maximum-key query options.
- Support OCI tag and digest references, optional registry authentication, and
  configurable registry hostnames.
- Support Python 3.10 through 3.14, including CPython and PyPy.

[unreleased]: https://github.com/Terradue/session-adapters/compare/v0.7.0...HEAD
[0.7.0]: https://github.com/Terradue/session-adapters/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/Terradue/session-adapters/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/Terradue/session-adapters/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/Terradue/session-adapters/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/Terradue/session-adapters/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/Terradue/session-adapters/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Terradue/session-adapters/releases/tag/v0.1.0
