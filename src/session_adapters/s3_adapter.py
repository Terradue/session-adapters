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

import io
from contextlib import suppress
from http import HTTPStatus
from typing import Any, Protocol, cast, final
from urllib.parse import parse_qs, urlparse

import boto3  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict
from requests import PreparedRequest
from requests.structures import CaseInsensitiveDict

from session_adapters.base import AbstractAdapter, ExtendedResponse
from session_adapters.http_conts import DEFAULT_ENCODING, ContentType, HTTPHeader

S3_SCHEME = "s3://"

DEFAULT_SERVICE_NAME = "s3"


def _to_http_response(boto3_reponse: Any, target_response: ExtendedResponse) -> None:
    target_response.send_status(HTTPStatus(boto3_reponse.get("HTTPStatusCode")))
    target_response.send_headers(boto3_reponse.get("ResponseMetadata", {}).get("HTTPHeaders", {}))


class _S3Request(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    bucket: str
    key: str
    query: dict[str, list[str]]
    # from original request
    headers: CaseInsensitiveDict[str | bytes]
    body: Any


class _ReadableBody(Protocol):
    def read(self, size: int = -1) -> bytes: ...

    def close(self) -> None: ...


class _StreamingBodyAdapter(io.RawIOBase):
    """
    Wrap botocore's StreamingBody to present a file-like object suitable for Response.raw
    and allow requests' iter_content to work efficiently without buffering all content.
    """

    def __init__(self, streaming_body: _ReadableBody) -> None:
        self._body = streaming_body
        self._closed = False

    def readable(self) -> bool:
        return True

    def read(self, size: int = -1) -> bytes:
        if self._closed:
            return b""
        return self._body.read() if size == -1 else self._body.read(size)

    def close(self) -> None:
        self._closed = True
        with suppress(Exception):
            self._body.close()


@final
class S3Adapter(AbstractAdapter[_S3Request]):
    """
    Transport adapter that handles s3:// URLs using a boto3 S3 client.
    Authentication is fully handled by boto3/botocore (env, shared config,
    profile, IAM role, etc.), or via the explicit session/client you pass in.
    """

    def __init__(
        self,
        region_name: str | None = None,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_session_token: str | None = None,
        endpoint_url: str | None = None,
        config: object | None = None,
    ) -> None:
        super().__init__()
        self.s3 = boto3.client(
            DEFAULT_SERVICE_NAME,
            region_name=region_name,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
            endpoint_url=endpoint_url,
            config=config,
        )

    def parse_request(self, request: PreparedRequest) -> _S3Request:
        parsed = urlparse(request.url)

        bucket = parsed.netloc
        if not bucket:
            raise TypeError("Missing bucket in s3:// URL")

        key = str(parsed.path).lstrip("/") if parsed.path else ""  # may be empty for "list"

        query = parse_qs(str(parsed.query)) if parsed.query else {}

        return _S3Request(
            bucket=str(bucket),
            key=key,
            query=query,
            headers=request.headers,
            body=request.body or b"",
        )

    def do_head(self, request: _S3Request, response: ExtendedResponse) -> None:
        boto3_reponse = self.s3.head_object(Bucket=request.bucket, Key=request.key)
        _to_http_response(boto3_reponse, response)
        response._content = b""

    def do_get(self, request: _S3Request, response: ExtendedResponse) -> None:
        boto3_reponse = None

        if request.key == "" or request.key.endswith("/"):
            # Directory-style listing
            boto3_reponse = self._list_objects(request.bucket, request.key, request.query)

            # Return a JSON-ish bytes payload listing keys and common prefixes.
            import json

            payload = {
                "KeyCount": boto3_reponse.get("KeyCount", 0),
                "IsTruncated": boto3_reponse.get("IsTruncated", False),
                "Contents": [
                    {"Key": o["Key"], "Size": o["Size"], "ETag": o.get("ETag")}
                    for o in boto3_reponse.get("Contents", [])
                ],
                "CommonPrefixes": [p["Prefix"] for p in boto3_reponse.get("CommonPrefixes", [])],
            }
            response._content = json.dumps(payload).encode(DEFAULT_ENCODING)
            response.send_headers(
                {
                    HTTPHeader.CONTENT_TYPE: ContentType.JSON,
                    HTTPHeader.CONTENT_LENGTH: str(len(response._content)),
                }
            )
        else:
            boto3_reponse = self.s3.get_object(
                Bucket=request.bucket,
                Key=request.key,
                **self._get_object_opts(request.query),
            )

            streaming_body = boto3_reponse["Body"] or io.BytesIO()
            # Prepare a file-like for Response.raw
            response.raw = _StreamingBodyAdapter(streaming_body)

        _to_http_response(boto3_reponse, response)

    def do_put(self, request: _S3Request, response: ExtendedResponse) -> None:
        body = request.body

        if isinstance(body, str):
            body = body.encode(DEFAULT_ENCODING)

        boto3_reponse = self.s3.put_object(
            Bucket=request.bucket,
            Key=request.key,
            Body=body,
            **self._put_object_opts(request.headers, request.query),
        )
        _to_http_response(boto3_reponse, response)

    def do_delete(self, request: _S3Request, response: ExtendedResponse) -> None:
        boto3_reponse = self.s3.delete_object(Bucket=request.bucket, Key=request.key)
        _to_http_response(boto3_reponse, response)

    def close(self) -> None:
        # No persistent sockets to close beyond what botocore manages, but keep hook for API parity.
        pass

    # ----- helpers -----

    def _get_object_opts(self, query: dict[str, list[str]]) -> dict[str, str]:
        opts = {}
        # Support simple Range requests: s3://bucket/key?range=bytes%3D0-99
        if "range" in query:
            opts["Range"] = query["range"][0]
        # Versioned object: ?versionId=...
        if "versionId" in query:
            opts["VersionId"] = query["versionId"][0]
        return opts

    def _put_object_opts(
        self, headers: CaseInsensitiveDict[str | bytes], query: dict[str, list[str]]
    ) -> dict[str, str | bytes]:
        opts: dict[str, str | bytes] = {}
        # ContentType, CacheControl, etc. can be passed via headers
        # Map a few common ones. You can extend at will.
        for hsrc, hdst in [
            (HTTPHeader.CONTENT_TYPE.value, "ContentType"),
            (HTTPHeader.CACHE_CONTROL.value, "CacheControl"),
            (HTTPHeader.CONTENT_ENCODING.value, "ContentEncoding"),
            (HTTPHeader.CONTENT_LANGUAGE.value, "ContentLanguage"),
            (HTTPHeader.CONTENT_DISPOSITION.value, "ContentDisposition"),
        ]:
            if hsrc in headers:
                opts[hdst] = headers[hsrc]
        # Server-side encryption via query (?sse=AES256, ?kmsKeyId=...)
        if query.get("sse", [None])[0]:
            val = query["sse"][0]
            if val == "AES256":
                opts["ServerSideEncryption"] = "AES256"
            elif val == "aws:kms":
                opts["ServerSideEncryption"] = "aws:kms"
                if "kmsKeyId" in query:
                    opts["SSEKMSKeyId"] = query["kmsKeyId"][0]
        return opts

    def _list_objects(
        self, bucket: str, prefix: str, query: dict[str, list[str]]
    ) -> dict[str, Any]:
        kwargs: dict[str, str | int] = {"Bucket": bucket, "Prefix": prefix}
        if "delimiter" in query:
            kwargs["Delimiter"] = query["delimiter"][0]
        if "maxKeys" in query:
            kwargs["MaxKeys"] = int(query["maxKeys"][0])
        return cast("dict[str, Any]", self.s3.list_objects_v2(**kwargs))
