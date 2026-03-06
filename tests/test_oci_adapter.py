from http import HTTPStatus

from requests import Request

from session_adapters.oci_adapter import OCIAdapter


class _FakeOrasClient:
    def __init__(self):
        self.last_pull = None
        self.last_push = None
        self.last_delete = None
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
        return None


def _new_adapter(monkeypatch):
    fake = _FakeOrasClient()
    monkeypatch.setattr(
        "session_adapters.oci_adapter.OrasClient", lambda *a, **k: fake
    )
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
    assert response.headers.get("CONTENT_TYPE") == "application/vnd.oci.image.manifest.v1+json"
    assert response.headers.get("Docker-Content-Digest") == "sha256:deadbeef"


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
    assert (
        fake.last_push["media_type"]
        == "application/vnd.oci.image.layer.v1.tar+gzip"
    )


def test_put_uses_default_media_type_when_no_accept_header(monkeypatch):
    adapter, fake = _new_adapter(monkeypatch)

    response = adapter.send(
        Request("PUT", "oci://my-registry.io/my-repo:latest", data=b"bytes").prepare()
    )

    assert response.status_code == HTTPStatus.CREATED
    assert fake.last_push["media_type"] == "application/octet-stream"


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
