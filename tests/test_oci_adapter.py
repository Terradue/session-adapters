# Copyright 2026 Terradue
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from base64 import b64encode
from http import HTTPStatus
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest
from pytest import MonkeyPatch
from requests import Request

from session_adapters.conainers_auth import Auth, ContainersAuth
from session_adapters.oci_adapter import OCIAdapter


class _FakeOrasClient:
    def __init__(self, hostname: str | None = None) -> None:
        self.hostname = hostname
        self.auth = SimpleNamespace(_auth_config={"auths": {}})
        self.session = Mock()
        self.login = Mock()
        self.logout = Mock(side_effect=lambda host: self.auth._auth_config["auths"].pop(host, None))
        self.last_pull: dict[str, str | None] | None = None
        self.last_push: dict[str, Any] | None = None
        self.last_delete: str | None = None
        self.pull_return: list[str] = []
        self.pull_raise: Exception | None = None

    def pull(self, target: str, outdir: str | None = None) -> list[str]:
        self.last_pull = {"target": target, "outdir": outdir}
        if self.pull_raise is not None:
            raise self.pull_raise
        return self.pull_return

    def push(self, ref: str, data: Any = None, media_type: str | None = None) -> None:
        self.last_push = {"ref": ref, "data": data, "media_type": media_type}

    def delete(self, ref: str) -> None:
        self.last_delete = ref


def _new_adapter(monkeypatch: MonkeyPatch) -> tuple[OCIAdapter, _FakeOrasClient]:
    fake = _FakeOrasClient()
    monkeypatch.setattr("session_adapters.oci_adapter.OrasClient", lambda *a, **k: fake)
    return OCIAdapter(), fake


# ---------------------------------------------------------------------------
# parse_request
# ---------------------------------------------------------------------------


def test_parse_missing_registry_becomes_bad_request(monkeypatch: MonkeyPatch) -> None:
    adapter, _ = _new_adapter(monkeypatch)

    response = adapter.send(Request("GET", "oci:///repo:tag").prepare())

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert b"Missing registry in oci:// URL" in response.content


def test_parse_missing_repository_becomes_bad_request(monkeypatch: MonkeyPatch) -> None:
    adapter, _ = _new_adapter(monkeypatch)

    response = adapter.send(Request("GET", "oci://my-registry.io/").prepare())

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert b"Missing repository in oci:// URL" in response.content


def test_parse_url_with_tag(monkeypatch: MonkeyPatch) -> None:
    adapter, _ = _new_adapter(monkeypatch)

    # parse_request should succeed without raising
    request = Request("GET", "oci://my-registry.io/my-repo:latest").prepare()
    parsed = adapter.parse_request(request)

    assert parsed.registry == "my-registry.io"
    assert parsed.repository == "my-repo"
    assert parsed.reference == ":latest"
    assert parsed.ref == "my-registry.io/my-repo:latest"


def test_parse_url_without_tag_has_no_reference(monkeypatch: MonkeyPatch) -> None:
    adapter, _ = _new_adapter(monkeypatch)

    request = Request("GET", "oci://my-registry.io/my-repo").prepare()
    parsed = adapter.parse_request(request)

    assert parsed.registry == "my-registry.io"
    assert parsed.repository == "my-repo"
    assert parsed.reference is None
    assert parsed.ref == "my-registry.io/my-repo"


def test_parse_url_with_digest_and_query(monkeypatch: MonkeyPatch) -> None:
    adapter, _ = _new_adapter(monkeypatch)

    request = Request(
        "GET",
        "oci://my-registry.io/my-org/my-repo@sha256:abc123?mediaType=application%2Fjson",
    ).prepare()
    parsed = adapter.parse_request(request)

    assert parsed.registry == "my-registry.io"
    assert parsed.repository == "my-org/my-repo"
    assert parsed.reference == "@sha256:abc123"
    assert parsed.query == {"mediaType": ["application/json"]}


# ---------------------------------------------------------------------------
# do_get
# ---------------------------------------------------------------------------


def test_get_returns_not_found_when_pull_is_empty(monkeypatch: MonkeyPatch) -> None:
    adapter, fake = _new_adapter(monkeypatch)
    fake.pull_return = []

    response = adapter.send(Request("GET", "oci://my-registry.io/my-repo:latest").prepare())

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert fake.last_pull is not None
    assert fake.last_pull["target"] == "my-registry.io/my-repo:latest"


def test_get_returns_ok_for_pulled_file(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    adapter, fake = _new_adapter(monkeypatch)

    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(b"oci-content")
    fake.pull_return = [str(artifact)]

    response = adapter.send(Request("GET", "oci://my-registry.io/my-repo:latest").prepare())

    assert response.status_code == HTTPStatus.OK
    assert response.raw.read() == b"oci-content"
    assert response.headers["Content-Length"] == str(len(b"oci-content"))


def test_get_returns_unauthorized_on_value_error(monkeypatch: MonkeyPatch) -> None:
    adapter, fake = _new_adapter(monkeypatch)
    fake.pull_raise = ValueError("Unauthorized: access denied")

    response = adapter.send(Request("GET", "oci://my-registry.io/my-repo:latest").prepare())

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_get_unknown_value_error_maps_to_method_not_allowed(monkeypatch: MonkeyPatch) -> None:
    adapter, fake = _new_adapter(monkeypatch)
    fake.pull_raise = ValueError("Unexpected parse error")

    response = adapter.send(Request("GET", "oci://my-registry.io/my-repo:latest").prepare())

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert b"Unexpected parse error" in response.content


# ---------------------------------------------------------------------------
# do_head
# ---------------------------------------------------------------------------


def test_head_returns_ok(monkeypatch: MonkeyPatch) -> None:
    adapter, fake = _new_adapter(monkeypatch)

    response = adapter.send(Request("HEAD", "oci://my-registry.io/my-repo:latest").prepare())

    assert response.status_code == HTTPStatus.OK
    assert fake.last_pull is not None
    assert fake.last_pull["target"] == "my-registry.io/my-repo:latest"


def test_head_with_manifest_method_populates_headers(monkeypatch: MonkeyPatch) -> None:
    adapter, fake = _new_adapter(monkeypatch)

    def _manifest(ref: str) -> dict[str, Any]:
        return {
            "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "digest": "sha256:deadbeef",
        }

    monkeypatch.setattr(fake, "manifest", _manifest, raising=False)

    response = adapter.send(Request("HEAD", "oci://my-registry.io/my-repo:latest").prepare())

    assert response.status_code == HTTPStatus.OK
    # The adapter sets this via HTTPHeader.CONTENT_TYPE.name ("CONTENT_TYPE"),
    # not the header value ("Content-Type"), so we check accordingly.
    assert response.headers.get("CONTENT_TYPE") == "application/vnd.oci.image.manifest.v1+json"
    assert response.headers.get("Docker-Content-Digest") == "sha256:deadbeef"


def test_head_uses_get_manifest_when_manifest_is_not_available(monkeypatch: MonkeyPatch) -> None:
    adapter, fake = _new_adapter(monkeypatch)
    monkeypatch.setattr(fake, "manifest", None, raising=False)

    def _get_manifest(ref: str) -> dict[str, Any]:
        return {"config": {"mediaType": "application/vnd.oci.image.config.v1+json"}}

    monkeypatch.setattr(fake, "get_manifest", _get_manifest, raising=False)

    response = adapter.send(Request("HEAD", "oci://my-registry.io/my-repo:latest").prepare())

    assert response.status_code == HTTPStatus.OK
    assert response.headers.get("CONTENT_TYPE") == "application/vnd.oci.image.config.v1+json"


def test_head_returns_not_found_on_manifest_error(monkeypatch: MonkeyPatch) -> None:
    adapter, fake = _new_adapter(monkeypatch)

    def _manifest(ref: str) -> dict[str, Any]:
        raise RuntimeError("registry unavailable")

    monkeypatch.setattr(fake, "manifest", _manifest, raising=False)

    response = adapter.send(Request("HEAD", "oci://my-registry.io/my-repo:latest").prepare())

    assert response.status_code == HTTPStatus.NOT_FOUND


# ---------------------------------------------------------------------------
# do_put
# ---------------------------------------------------------------------------


def test_put_pushes_artifact(monkeypatch: MonkeyPatch) -> None:
    adapter, fake = _new_adapter(monkeypatch)

    response = adapter.send(
        Request(
            "PUT",
            "oci://my-registry.io/my-repo:latest",
            data=b"artifact-bytes",
            headers={"Accept": "application/vnd.oci.image.layer.v1.tar+gzip"},
        ).prepare()
    )

    assert response.status_code == HTTPStatus.CREATED
    assert fake.last_push is not None
    assert fake.last_push["ref"] == "my-registry.io/my-repo:latest"
    assert fake.last_push["data"] == b"artifact-bytes"
    assert fake.last_push["media_type"] == "application/vnd.oci.image.layer.v1.tar+gzip"


def test_put_uses_default_media_type_when_no_accept_header(monkeypatch: MonkeyPatch) -> None:
    adapter, fake = _new_adapter(monkeypatch)

    response = adapter.send(
        Request("PUT", "oci://my-registry.io/my-repo:latest", data=b"bytes").prepare()
    )

    assert response.status_code == HTTPStatus.CREATED
    assert fake.last_push is not None
    assert fake.last_push["media_type"] == "application/octet-stream"


def test_put_falls_back_to_minimal_push_signature(monkeypatch: MonkeyPatch) -> None:
    adapter, fake = _new_adapter(monkeypatch)
    calls = {"count": 0}

    def _push(*args: Any, **kwargs: Any) -> None:
        calls["count"] += 1
        if calls["count"] == 1:
            raise TypeError("unsupported signature")
        fake.last_push = {"ref": args[0], "data": args[1], "media_type": None}

    monkeypatch.setattr(fake, "push", _push)

    response = adapter.send(
        Request("PUT", "oci://my-registry.io/my-repo:latest", data=b"bytes").prepare()
    )

    assert response.status_code == HTTPStatus.CREATED
    expected_attempts = 2
    assert calls["count"] == expected_attempts
    assert fake.last_push is not None
    assert fake.last_push["ref"] == "my-registry.io/my-repo:latest"
    assert fake.last_push["data"] == b"bytes"


def test_put_returns_service_unavailable_when_no_compatible_push(monkeypatch: MonkeyPatch) -> None:
    adapter, fake = _new_adapter(monkeypatch)

    def _push(*args: Any, **kwargs: Any) -> None:
        if kwargs:
            raise TypeError("unsupported")
        raise AttributeError("missing push")

    monkeypatch.setattr(fake, "push", _push)

    response = adapter.send(
        Request("PUT", "oci://my-registry.io/my-repo:latest", data=b"bytes").prepare()
    )

    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert b"compatible .push" in response.content


# ---------------------------------------------------------------------------
# do_delete
# ---------------------------------------------------------------------------


def test_delete_removes_artifact(monkeypatch: MonkeyPatch) -> None:
    adapter, fake = _new_adapter(monkeypatch)

    response = adapter.send(Request("DELETE", "oci://my-registry.io/my-repo:latest").prepare())

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert fake.last_delete == "my-registry.io/my-repo:latest"


def test_delete_returns_method_not_allowed_when_client_has_no_delete(
    monkeypatch: MonkeyPatch,
) -> None:
    adapter, fake = _new_adapter(monkeypatch)
    # Override the instance attribute to shadow the class method, making getattr return None
    monkeypatch.setattr(fake, "delete", None)

    response = adapter.send(Request("DELETE", "oci://my-registry.io/my-repo:latest").prepare())

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED


def test_delete_returns_bad_gateway_when_client_delete_fails(monkeypatch: MonkeyPatch) -> None:
    adapter, fake = _new_adapter(monkeypatch)

    def _delete(_: str) -> None:
        raise RuntimeError("cannot delete")

    monkeypatch.setattr(fake, "delete", _delete)

    response = adapter.send(Request("DELETE", "oci://my-registry.io/my-repo:latest").prepare())

    assert response.status_code == HTTPStatus.BAD_GATEWAY
    assert b"cannot delete" in response.content


@pytest.mark.parametrize(
    ("repository", "expected"),
    [
        ("team/sub/repo", "repo"),
        ("team/sub/other", "sub"),
        ("team/other", "team"),
        ("team-other/repo", "host"),
    ],
)
def test_auth_uses_most_specific_scope(
    monkeypatch: MonkeyPatch, repository: str, expected: str
) -> None:
    auths = {
        f"registry.io{scope}": {"auth": b64encode(f"{user}:secret:colon".encode()).decode()}
        for scope, user in [
            ("", "host"),
            ("/team", "team"),
            ("/team/sub", "sub"),
            ("/team/sub/repo", "repo"),
        ]
    }
    adapter = OCIAdapter(ContainersAuth.model_validate({"auths": auths}))
    monkeypatch.setattr("session_adapters.oci_adapter.OrasClient", _FakeOrasClient)
    request = adapter.parse_request(Request("GET", f"oci://registry.io/{repository}:tag").prepare())
    client = adapter._get_oras_with_optional_auth(request)
    client.login.assert_called_once_with(
        username=expected, password="secret:colon", hostname="registry.io"
    )


@pytest.mark.parametrize("entry", [{}, {"identitytoken": "token"}, {"auth": "dXNlcjo="}])
def test_incomplete_auth_is_anonymous(monkeypatch: MonkeyPatch, entry: dict[str, str]) -> None:
    adapter = OCIAdapter(ContainersAuth.model_validate({"auths": {"registry.io": entry}}))
    monkeypatch.setattr("session_adapters.oci_adapter.OrasClient", _FakeOrasClient)
    request = adapter.parse_request(Request("GET", "oci://registry.io/team/repo").prepare())
    client = adapter._get_oras_with_optional_auth(request)
    assert client.hostname is None
    client.login.assert_not_called()


def test_sibling_namespace_credentials_are_not_used(monkeypatch: MonkeyPatch) -> None:
    adapter = OCIAdapter(
        ContainersAuth.model_validate(
            {"auths": {"https://registry.io/private": {"auth": "dXNlcjpwYXNz"}}}
        )
    )
    monkeypatch.setattr("session_adapters.oci_adapter.OrasClient", _FakeOrasClient)
    request = adapter.parse_request(Request("GET", "oci://registry.io/public/repo").prepare())
    client = adapter._get_oras_with_optional_auth(request)
    client.login.assert_not_called()
    assert client.hostname is None


@pytest.mark.parametrize("missing", [False, True])
def test_registry_helper_uses_docker_store(monkeypatch: MonkeyPatch, missing: bool) -> None:
    from docker.credentials import CredentialsNotFound  # type: ignore[import-untyped]

    store = Mock()
    store.get.return_value = {"Username": "helper", "Secret": "secret"}
    if missing:
        store.get.side_effect = CredentialsNotFound("missing")
    factory = Mock(return_value=store)
    monkeypatch.setattr("docker.credentials.Store", factory)
    monkeypatch.setattr("session_adapters.oci_adapter.OrasClient", _FakeOrasClient)
    adapter = OCIAdapter(
        ContainersAuth.model_validate(
            {
                "auths": {"registry.io/team": {"auth": "dXNlcjpwYXNz"}},
                "credHelpers": {"registry.io": "test"},
            }
        )
    )
    request = adapter.parse_request(Request("GET", "oci://registry.io/team/repo").prepare())
    client = adapter._get_oras_with_optional_auth(request)
    factory.assert_called_once_with("test", environment=None)
    store.get.assert_called_once_with("registry.io")
    client.login.assert_called_once_with(
        username="user" if missing else "helper",
        password="pass" if missing else "secret",
        hostname="registry.io",
    )


def test_failed_login_closes_client_and_returns_anonymous(monkeypatch: MonkeyPatch) -> None:
    adapter = OCIAdapter(
        ContainersAuth.model_validate({"auths": {"registry.io": {"auth": "dXNlcjpwYXNz"}}})
    )
    authenticated = _FakeOrasClient("registry.io")
    authenticated.login.side_effect = RuntimeError("login failed")
    anonymous = _FakeOrasClient()
    monkeypatch.setattr(
        "session_adapters.oci_adapter.OrasClient", Mock(side_effect=[authenticated, anonymous])
    )
    request = adapter.parse_request(Request("GET", "oci://registry.io/repo").prepare())
    assert adapter._get_oras_with_optional_auth(request) is anonymous
    authenticated.logout.assert_called_once_with("registry.io")
    authenticated.session.close.assert_called_once()
    anonymous.login.assert_not_called()


def test_logout_clears_all_hosts_and_closes_session(monkeypatch: MonkeyPatch) -> None:
    adapter, client = _new_adapter(monkeypatch)
    client.auth._auth_config["auths"] = {"first.io": {}, "second.io": {}}
    adapter._logout(client)
    assert not client.auth._auth_config["auths"]
    expected_logouts = 2
    assert client.logout.call_count == expected_logouts
    client.session.close.assert_called_once()


def test_helper_failure_returns_anonymous(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("docker.credentials.Store", Mock(side_effect=RuntimeError("unavailable")))
    monkeypatch.setattr("session_adapters.oci_adapter.OrasClient", _FakeOrasClient)
    adapter = OCIAdapter(ContainersAuth.model_validate({"credHelpers": {"registry.io": "missing"}}))
    request = adapter.parse_request(Request("GET", "oci://registry.io/repo").prepare())
    client = adapter._get_oras_with_optional_auth(request)
    client.login.assert_not_called()
    assert client.hostname is None


def test_logout_continues_after_failure(monkeypatch: MonkeyPatch) -> None:
    adapter, client = _new_adapter(monkeypatch)
    client.auth._auth_config["auths"] = {"first.io": {}, "second.io": {}}
    client.logout.side_effect = RuntimeError("logout failed")
    adapter._logout(client)
    assert {call.args[0] for call in client.logout.call_args_list} == {"first.io", "second.io"}
    client.session.close.assert_called_once()


@pytest.mark.parametrize("method", ["GET", "HEAD", "PUT", "DELETE"])
def test_operations_close_session(monkeypatch: MonkeyPatch, method: str) -> None:
    adapter, client = _new_adapter(monkeypatch)
    adapter.send(Request(method, "oci://registry.io/repo").prepare())
    client.session.close.assert_called_once()


@pytest.mark.parametrize("scheme", ["", "http://", "https://", "oci://", "custom+registry://"])
@pytest.mark.parametrize("repository", ["team/repo", "team-other/repo"])
def test_auth_key_normalization_preserves_port_and_namespace(
    monkeypatch: MonkeyPatch, scheme: str, repository: str
) -> None:
    adapter = OCIAdapter(
        ContainersAuth.model_validate(
            {"auths": {f"{scheme}registry.io:5000/team/": {"auth": "dXNlcjpwYXNz"}}}
        )
    )
    monkeypatch.setattr("session_adapters.oci_adapter.OrasClient", _FakeOrasClient)
    request = adapter.parse_request(
        Request("GET", f"oci://registry.io:5000/{repository}:tag").prepare()
    )
    client = adapter._get_oras_with_optional_auth(request)
    if repository == "team/repo":
        client.login.assert_called_once_with(
            username="user", password="pass", hostname="registry.io:5000"
        )
    else:
        client.login.assert_not_called()
        assert client.hostname is None


@pytest.mark.parametrize("auths", [None, {}])
def test_add_auth_initializes_config_and_resolves_credentials(
    auths: dict[str, Auth] | None,
) -> None:
    config = ContainersAuth(auths=auths)
    config.add_auth("registry.io:5000", "usér", "päss:word")
    adapter = OCIAdapter(containers_auth=config)
    request = adapter.parse_request(Request("GET", "oci://registry.io:5000/team/repo").prepare())
    resolved = adapter._resolve_request_auth(request)
    assert resolved is not None
    assert resolved["username"] == "usér"
    assert resolved["password"] == "päss:word"
    assert config.auths is not None
    assert config.auths["registry.io:5000"].identitytoken is None


def test_add_auth_replaces_only_target_entry() -> None:
    config = ContainersAuth.model_validate(
        {
            "auths": {
                "registry.io": {"identitytoken": "old-token"},
                "other.io": {"auth": "dXNlcjpwYXNz"},
            },
            "credHelpers": {"other.io": "pass"},
        }
    )
    entries = config.auths
    assert entries is not None
    other = entries["other.io"]
    config.add_auth("registry.io", "new-user", "new-password")
    assert config.auths is entries
    assert config.auths["other.io"] is other
    assert config.cred_helpers == {"other.io": "pass"}
    assert config.auths["registry.io"].model_dump(exclude_none=True) == {
        "auth": b64encode(b"new-user:new-password").decode("ascii")
    }
