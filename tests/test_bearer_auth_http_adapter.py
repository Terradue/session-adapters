from unittest.mock import patch

from requests import Request, Response
from requests.adapters import HTTPAdapter

from session_adapters.bearer_auth_http_adapter import BearerAuthHTTPAdapter


def test_send_sets_bearer_authorization_header_and_delegates():
    adapter = BearerAuthHTTPAdapter("test-token")
    request = Request(
        "GET",
        "https://example.com/resource",
        headers={"Authorization": "Basic old-credentials"},
    ).prepare()
    expected_response = Response()

    with patch.object(HTTPAdapter, "send", return_value=expected_response) as send:
        response = adapter.send(request, timeout=10)

    assert request.headers["Authorization"] == "Bearer test-token"
    send.assert_called_once_with(request, timeout=10)
    assert response is expected_response
