from http import HTTPStatus

from requests import PreparedRequest, Request

from session_adapters.base import AbstractAdapter, ExtendedResponse
from session_adapters.http_conts import HTTPHeader


def _prepare(method: str, url: str = "http://example.test/resource") -> PreparedRequest:
    return Request(method=method, url=url).prepare()


class _DummyAdapter(AbstractAdapter[PreparedRequest]):
    def __init__(self, raise_in_parse=False, raise_in_get=False):
        super().__init__()
        self.raise_in_parse = raise_in_parse
        self.raise_in_get = raise_in_get
        self.called = []

    def parse_request(self, request: PreparedRequest) -> PreparedRequest:
        if self.raise_in_parse:
            raise TypeError("bad request")
        return request

    def do_get(self, request: PreparedRequest, response: ExtendedResponse):
        self.called.append("GET")
        if self.raise_in_get:
            raise RuntimeError("boom")
        response.send_status(HTTPStatus.OK)

    def do_head(self, request: PreparedRequest, response: ExtendedResponse):
        self.called.append("HEAD")
        response.send_status(HTTPStatus.OK)

    def do_put(self, request: PreparedRequest, response: ExtendedResponse):
        self.called.append("PUT")
        response.send_status(HTTPStatus.CREATED)

    def do_delete(self, request: PreparedRequest, response: ExtendedResponse):
        self.called.append("DELETE")
        response.send_status(HTTPStatus.NO_CONTENT)


def test_send_dispatches_get():
    adapter = _DummyAdapter()

    response = adapter.send(_prepare("GET"))

    assert response.status_code == HTTPStatus.OK
    assert adapter.called == ["GET"]


def test_send_returns_method_not_allowed_for_supported_but_unhandled_method():
    adapter = _DummyAdapter()

    response = adapter.send(_prepare("POST"))

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert response.headers[HTTPHeader.ALLOW.value] == "GET, HEAD, PUT, DELETE"
    assert adapter.called == []


def test_send_maps_invalid_method_to_method_not_allowed_error():
    adapter = _DummyAdapter()

    response = adapter.send(_prepare("BREW"))

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert response.headers[HTTPHeader.CONTENT_TYPE.value] == "text/plain"
    assert b"valid HTTPMethod" in response.content


def test_send_maps_parse_type_error_to_bad_request():
    adapter = _DummyAdapter(raise_in_parse=True)

    response = adapter.send(_prepare("GET"))

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.headers[HTTPHeader.CONTENT_TYPE.value] == "text/plain"
    assert response.content == b"bad request"


def test_send_maps_unexpected_error_to_internal_server_error():
    adapter = _DummyAdapter(raise_in_get=True)

    response = adapter.send(_prepare("GET"))

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response.headers[HTTPHeader.CONTENT_TYPE.value] == "text/plain"
    assert response.content == b"boom"
