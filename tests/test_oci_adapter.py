from http import HTTPStatus

from requests import Request

from session_adapters.oci_adapter import OCIAdapter


class _FakeOrasClient:
    def __init__(self):
        self.last_pull = None
        self.last_push = None
        self.last_delete = None
        self.logout_called = False
        self.pull_return = []
        self.pull_raise = None

    def login(self, hostname, username, password):
        return {"ok": True}

    def pull(self, target, outdir=None):
        self.last_pull = {"target": target, "outdir": outdir}
        if self.pull_raise is not None:
            raise self.pull_raise
        return self.pull_return

    def push(self, ref, data=None, media_type=None):
        self.last_push = {"ref": ref, "data": data, "media_type": media_type}
        return None

    def delete(self, ref):
        self.last_delete = ref
        return None

    def logout(self):
        self.logout_called = True
        return None


def _new_adapter(monkeypatch):
    fake = _FakeOrasClient()
    monkeypatch.setattr("session_adapters.oci_adapter.OrasClient", lambda *a, **k: fake)
    return OCIAdapter(), fake


# ---------------------------------------------------------------------------
# parse_request
# ---------------------------------------------------------------------------


def test_parse_missing_registry_becomes_bad_request(monkeypatch):
    adapter, _ = _new_adapter(monkeypatch)

    response = adapter.send(Request("GET", "oci:///repo:tag").prepare())

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert b"Missing registry in oci:// URL" in response.content


def test_parse_missing_repository_becomes_bad_request(monkeypatch):
    adapter, _ = _new_adapter(monkeypatch)

    response = adapter.send(Request("GET", "oci://my-registry.io/").prepare())

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert b"Missing repository in oci:// URL" in response.content


def test_parse_url_with_tag(monkeypatch):
    adapter, _ = _new_adapter(monkeypatch)

    # parse_request should succeed without raising
    request = Request("GET", "oci://my-registry.io/my-repo:latest").prepare()
    parsed = adapter.parse_request(request)

    assert parsed.registry == "my-registry.io"
    assert parsed.repository == "my-repo"
    assert parsed.reference == ":latest"
    assert parsed.ref == "my-registry.io/my-repo:latest"


def test_parse_url_without_tag_has_no_reference(monkeypatch):
    adapter, _ = _new_adapter(monkeypatch)

    request = Request("GET", "oci://my-registry.io/my-repo").prepare()
    parsed = adapter.parse_request(request)

    assert parsed.registry == "my-registry.io"
    assert parsed.repository == "my-repo"
    assert parsed.reference is None
    assert parsed.ref == "my-registry.io/my-repo"


def test_parse_url_with_digest_and_query(monkeypatch):
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


def test_get_returns_not_found_when_pull_is_empty(monkeypatch):
    adapter, fake = _new_adapter(monkeypatch)
    fake.pull_return = []

    response = adapter.send(
        Request("GET", "oci://my-registry.io/my-repo:latest").prepare()
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert fake.last_pull["target"] == "my-registry.io/my-repo:latest"


def test_get_returns_ok_for_pulled_file(monkeypatch, tmp_path):
    adapter, fake = _new_adapter(monkeypatch)

    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(b"oci-content")
    fake.pull_return = [str(artifact)]

    response = adapter.send(
        Request("GET", "oci://my-registry.io/my-repo:latest").prepare()
    )

    assert response.status_code == HTTPStatus.OK
    assert response.raw.read() == b"oci-content"
    assert response.headers["Content-Length"] == str(len(b"oci-content"))


def test_get_returns_unauthorized_on_value_error(monkeypatch):
    adapter, fake = _new_adapter(monkeypatch)
    fake.pull_raise = ValueError("Unauthorized: access denied")

    response = adapter.send(
        Request("GET", "oci://my-registry.io/my-repo:latest").prepare()
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_get_unknown_value_error_maps_to_method_not_allowed(monkeypatch):
    adapter, fake = _new_adapter(monkeypatch)
    fake.pull_raise = ValueError("Unexpected parse error")

    response = adapter.send(
        Request("GET", "oci://my-registry.io/my-repo:latest").prepare()
    )

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert b"Unexpected parse error" in response.content


# ---------------------------------------------------------------------------
# do_head
# ---------------------------------------------------------------------------


def test_head_returns_ok(monkeypatch):
    adapter, fake = _new_adapter(monkeypatch)

    response = adapter.send(
        Request("HEAD", "oci://my-registry.io/my-repo:latest").prepare()
    )

    assert response.status_code == HTTPStatus.OK
    assert fake.last_pull["target"] == "my-registry.io/my-repo:latest"


def test_head_with_manifest_method_populates_headers(monkeypatch):
    adapter, fake = _new_adapter(monkeypatch)

    def _manifest(ref):
        return {
            "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "digest": "sha256:deadbeef",
        }

    fake.manifest = _manifest

    response = adapter.send(
        Request("HEAD", "oci://my-registry.io/my-repo:latest").prepare()
    )

    assert response.status_code == HTTPStatus.OK
    # The adapter sets this via HTTPHeader.CONTENT_TYPE.name ("CONTENT_TYPE"),
    # not the header value ("Content-Type"), so we check accordingly.
    assert (
        response.headers.get("CONTENT_TYPE")
        == "application/vnd.oci.image.manifest.v1+json"
    )
    assert response.headers.get("Docker-Content-Digest") == "sha256:deadbeef"


def test_head_uses_get_manifest_when_manifest_is_not_available(monkeypatch):
    adapter, fake = _new_adapter(monkeypatch)
    fake.manifest = None

    def _get_manifest(ref):
        return {"config": {"mediaType": "application/vnd.oci.image.config.v1+json"}}

    fake.get_manifest = _get_manifest

    response = adapter.send(
        Request("HEAD", "oci://my-registry.io/my-repo:latest").prepare()
    )

    assert response.status_code == HTTPStatus.OK
    assert (
        response.headers.get("CONTENT_TYPE")
        == "application/vnd.oci.image.config.v1+json"
    )


def test_head_returns_not_found_on_manifest_error(monkeypatch):
    adapter, fake = _new_adapter(monkeypatch)

    def _manifest(ref):
        raise RuntimeError("registry unavailable")

    fake.manifest = _manifest

    response = adapter.send(
        Request("HEAD", "oci://my-registry.io/my-repo:latest").prepare()
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


# ---------------------------------------------------------------------------
# do_put
# ---------------------------------------------------------------------------


def test_put_pushes_artifact(monkeypatch):
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
    assert fake.last_push["ref"] == "my-registry.io/my-repo:latest"
    assert fake.last_push["data"] == b"artifact-bytes"
    assert fake.last_push["media_type"] == "application/vnd.oci.image.layer.v1.tar+gzip"


def test_put_uses_default_media_type_when_no_accept_header(monkeypatch):
    adapter, fake = _new_adapter(monkeypatch)

    response = adapter.send(
        Request("PUT", "oci://my-registry.io/my-repo:latest", data=b"bytes").prepare()
    )

    assert response.status_code == HTTPStatus.CREATED
    assert fake.last_push["media_type"] == "application/octet-stream"


def test_put_falls_back_to_minimal_push_signature(monkeypatch):
    adapter, fake = _new_adapter(monkeypatch)
    calls = {"count": 0}

    def _push(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise TypeError("unsupported signature")
        fake.last_push = {"ref": args[0], "data": args[1], "media_type": None}
        return None

    fake.push = _push

    response = adapter.send(
        Request("PUT", "oci://my-registry.io/my-repo:latest", data=b"bytes").prepare()
    )

    assert response.status_code == HTTPStatus.CREATED
    assert calls["count"] == 2
    assert fake.last_push["ref"] == "my-registry.io/my-repo:latest"
    assert fake.last_push["data"] == b"bytes"


def test_put_returns_service_unavailable_when_no_compatible_push(monkeypatch):
    adapter, fake = _new_adapter(monkeypatch)

    def _push(*args, **kwargs):
        if kwargs:
            raise TypeError("unsupported")
        raise AttributeError("missing push")

    fake.push = _push

    response = adapter.send(
        Request("PUT", "oci://my-registry.io/my-repo:latest", data=b"bytes").prepare()
    )

    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert b"compatible .push" in response.content


# ---------------------------------------------------------------------------
# do_delete
# ---------------------------------------------------------------------------


def test_delete_removes_artifact(monkeypatch):
    adapter, fake = _new_adapter(monkeypatch)

    response = adapter.send(
        Request("DELETE", "oci://my-registry.io/my-repo:latest").prepare()
    )

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert fake.last_delete == "my-registry.io/my-repo:latest"


def test_delete_returns_method_not_allowed_when_client_has_no_delete(monkeypatch):
    adapter, fake = _new_adapter(monkeypatch)
    # Override the instance attribute to shadow the class method, making getattr return None
    fake.delete = None

    response = adapter.send(
        Request("DELETE", "oci://my-registry.io/my-repo:latest").prepare()
    )

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED


def test_delete_returns_bad_gateway_when_client_delete_fails(monkeypatch):
    adapter, fake = _new_adapter(monkeypatch)

    def _delete(_):
        raise RuntimeError("cannot delete")

    fake.delete = _delete

    response = adapter.send(
        Request("DELETE", "oci://my-registry.io/my-repo:latest").prepare()
    )

    assert response.status_code == HTTPStatus.BAD_GATEWAY
    assert b"cannot delete" in response.content


def test_close_logs_out_client(monkeypatch):
    adapter, fake = _new_adapter(monkeypatch)

    adapter.close()

    assert fake.logout_called is True
