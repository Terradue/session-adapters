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

import json
from http import HTTPStatus
from typing import Any

from pytest import MonkeyPatch
from requests import Request

from session_adapters.s3_adapter import S3Adapter


class _FakeStreamingBody:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload
        self.closed = False

    def read(self, size: int = -1) -> bytes:
        if size == -1:
            return self._payload
        return self._payload[:size]

    def close(self) -> None:
        self.closed = True


class _FakeS3Client:
    def __init__(self) -> None:
        self.last_head: dict[str, Any] | None = None
        self.last_get: dict[str, Any] | None = None
        self.last_put: dict[str, Any] | None = None
        self.last_delete: dict[str, Any] | None = None
        self.last_list: dict[str, Any] | None = None

    def head_object(self, **kwargs: Any) -> dict[str, Any]:
        self.last_head = kwargs
        return {
            "HTTPStatusCode": 200,
            "ResponseMetadata": {"HTTPHeaders": {"x-head": "yes"}},
        }

    def get_object(self, **kwargs: Any) -> dict[str, Any]:
        self.last_get = kwargs
        return {
            "HTTPStatusCode": 200,
            "Body": _FakeStreamingBody(b"abc123"),
            "ResponseMetadata": {"HTTPHeaders": {"x-get": "yes"}},
        }

    def put_object(self, **kwargs: Any) -> dict[str, Any]:
        self.last_put = kwargs
        return {
            "HTTPStatusCode": 201,
            "ResponseMetadata": {"HTTPHeaders": {"x-put": "yes"}},
        }

    def delete_object(self, **kwargs: Any) -> dict[str, Any]:
        self.last_delete = kwargs
        return {
            "HTTPStatusCode": 204,
            "ResponseMetadata": {"HTTPHeaders": {"x-delete": "yes"}},
        }

    def list_objects_v2(self, **kwargs: Any) -> dict[str, Any]:
        self.last_list = kwargs
        return {
            "HTTPStatusCode": 200,
            "KeyCount": 1,
            "IsTruncated": False,
            "Contents": [{"Key": "folder/file.txt", "Size": 7, "ETag": "etag123"}],
            "CommonPrefixes": [{"Prefix": "folder/sub/"}],
            "ResponseMetadata": {"HTTPHeaders": {}},
        }


def _new_adapter(monkeypatch: MonkeyPatch) -> tuple[S3Adapter, _FakeS3Client]:
    fake = _FakeS3Client()
    monkeypatch.setattr("session_adapters.s3_adapter.boto3.client", lambda *a, **k: fake)
    return S3Adapter(), fake


def test_parse_missing_bucket_becomes_bad_request(monkeypatch: MonkeyPatch) -> None:
    adapter, _ = _new_adapter(monkeypatch)

    response = adapter.send(Request("GET", "s3:///some-key").prepare())

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert b"Missing bucket in s3:// URL" in response.content


def test_get_object_uses_query_options(monkeypatch: MonkeyPatch) -> None:
    adapter, fake = _new_adapter(monkeypatch)

    response = adapter.send(
        Request("GET", "s3://my-bucket/path/file.txt?range=bytes%3D0-9&versionId=v1").prepare()
    )

    assert response.status_code == HTTPStatus.OK
    assert response.raw.read() == b"abc123"
    assert fake.last_get == {
        "Bucket": "my-bucket",
        "Key": "path/file.txt",
        "Range": "bytes=0-9",
        "VersionId": "v1",
    }


def test_put_object_maps_headers_and_sse(monkeypatch: MonkeyPatch) -> None:
    adapter, fake = _new_adapter(monkeypatch)
    request = Request(
        "PUT",
        "s3://my-bucket/path/file.txt?sse=aws:kms&kmsKeyId=my-key",
        data="hello",
        headers={
            "Content-Type": "text/plain",
            "Cache-Control": "max-age=60",
        },
    ).prepare()

    response = adapter.send(request)

    assert response.status_code == HTTPStatus.CREATED
    assert fake.last_put == {
        "Bucket": "my-bucket",
        "Key": "path/file.txt",
        "Body": b"hello",
        "ContentType": "text/plain",
        "CacheControl": "max-age=60",
        "ServerSideEncryption": "aws:kms",
        "SSEKMSKeyId": "my-key",
    }


def test_list_prefix_returns_json_payload(monkeypatch: MonkeyPatch) -> None:
    adapter, fake = _new_adapter(monkeypatch)

    response = adapter.send(
        Request("GET", "s3://my-bucket/folder/?delimiter=%2F&maxKeys=2").prepare()
    )

    payload = json.loads(response.content.decode("utf-8"))
    assert response.status_code == HTTPStatus.OK
    assert response.headers["Content-Type"] == "application/json"
    assert payload["KeyCount"] == 1
    assert payload["Contents"][0]["Key"] == "folder/file.txt"
    assert payload["CommonPrefixes"] == ["folder/sub/"]
    assert fake.last_list == {
        "Bucket": "my-bucket",
        "Prefix": "folder/",
        "Delimiter": "/",
        "MaxKeys": 2,
    }


def test_get_object_with_empty_body_returns_readable_stream(monkeypatch: MonkeyPatch) -> None:
    adapter, fake = _new_adapter(monkeypatch)

    def get_object(**kwargs: Any) -> dict[str, Any]:
        return {"HTTPStatusCode": 200, "Body": None}

    monkeypatch.setattr(fake, "get_object", get_object)
    response = adapter.send(Request("GET", "s3://my-bucket/empty.txt").prepare())

    assert response.status_code == HTTPStatus.OK
    assert response.content == b""
    response.close()
