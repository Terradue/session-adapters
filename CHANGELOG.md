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

[unreleased]: https://github.com/Terradue/session-adapters/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/Terradue/session-adapters/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/Terradue/session-adapters/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/Terradue/session-adapters/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Terradue/session-adapters/releases/tag/v0.1.0
