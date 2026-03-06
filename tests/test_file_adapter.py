from http import HTTPStatus

from requests import Request

from session_adapters.file_adapter import FileAdapter


def test_parse_request_rejects_host_component():
    adapter = FileAdapter()
    request = Request("GET", "file://example.com/tmp/test.txt").prepare()

    try:
        adapter.parse_request(request)
    except TypeError as exc:
        assert "hostname components are not allowed" in str(exc)
    else:
        raise AssertionError("TypeError was expected for non-localhost file URL")


def test_put_get_delete_roundtrip(tmp_path):
    adapter = FileAdapter()
    target = tmp_path / "nested" / "sample.txt"
    url = target.as_uri()

    put_response = adapter.send(Request("PUT", url, data="hello world").prepare())
    assert put_response.status_code is None
    assert target.read_text() == "hello world"

    get_response = adapter.send(Request("GET", url).prepare())
    assert get_response.status_code == HTTPStatus.OK
    assert get_response.raw.read() == b"hello world"
    assert get_response.headers["Content-Length"] == str(len("hello world"))

    delete_response = adapter.send(Request("DELETE", url).prepare())
    assert delete_response.status_code == HTTPStatus.OK
    assert not target.exists()


def test_head_missing_file_returns_not_found(tmp_path):
    adapter = FileAdapter()
    missing = (tmp_path / "does-not-exist.txt").as_uri()

    response = adapter.send(Request("HEAD", missing).prepare())

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert b"does not exist on the local File System" in response.content
