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

from session_adapters.base import (
    AbstractAdapter,
    ExtendedResponse,
    __DEFAULT_READ_MODE__,
)
from session_adapters.http_conts import DEFAULT_ENCODING, HTTPHeader, ContentType
from http import HTTPStatus
from loguru import logger
from pathlib import Path
from oras.client import OrasClient
from pydantic import BaseModel, computed_field, ConfigDict
from requests import PreparedRequest
from requests.adapters import CaseInsensitiveDict
from typing import Any, Dict, final, List, Optional
from urllib.parse import urlparse, parse_qs

import io

OCI_SCHEME = "oci://"


class _OCIRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    registry: str
    repository: str
    reference: Optional[str] = None
    query: Dict[str, List[str]]
    # from original request
    headers: CaseInsensitiveDict
    body: Any

    @computed_field
    @property
    def ref(self) -> str:
        """
        The OrasClient typically needs a combined ref like: "{registry}/{repository}:{tag}" or "@sha256:..."
        """
        return f"{self.registry}/{self.repository}{self.reference or ''}"


@final
class OCIAdapter(AbstractAdapter[_OCIRequest]):
    """
    A requests Transport Adapter that handles oci:// URLs using an OrasClient.

    Auth: pass in a pre-configured, authenticated OrasClient (recommended).
    You can also pass username/password/token and, if your OrasClient exposes a
    login() or similar, you may adapt the constructor to call it.
    """

    def __init__(
        self,
        hostname: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        outdir: Optional[str] = None,
    ):
        super(OCIAdapter, self).__init__()

        self.hostname = hostname
        self.username = username
        self.password = password
        self.outdir = outdir

    def _get_oras_with_optional_auth(self) -> OrasClient:
        try:
            if self.hostname and self.username and self.password:
                logger.debug(f"OCI {self.username}@{self.hostname} login...")

                client: OrasClient = OrasClient(hostname=self.hostname)
                res = client.login(username=self.username, password=self.password)

                logger.debug(
                    f"OCI login {self.username}@{self.hostname} response: {res}"
                )

                return client
        except Exception as e:
            # retry anonymous
            logger.warning(f"OCI login/auth handshake failed -> retry anonymously: {e}")
            pass

        return OrasClient()

    def _logout(self, client: OrasClient):
        if self.hostname:
            client.logout(self.hostname)

    def parse_request(self, request: PreparedRequest) -> _OCIRequest:
        """
        Parse: oci://registry/repository[:tag|@digest]
        Returns (registry, repository, reference) where reference includes the ":" or "@"
        """
        # Parse oci://registry/repo[:tag|@digest]
        parsed = urlparse(request.url)

        registry = str(parsed.netloc) if parsed.netloc else None
        if not registry:
            raise TypeError("Missing registry in oci:// URL")

        # Strip leading slash
        path = str(parsed.path).lstrip("/") if parsed.path else None
        if not path:
            raise TypeError("Missing repository in oci:// URL")

        # repository + optional ref
        # Digest refs use "@", while tag refs use ":".
        digest_idx = path.rfind("@")
        if digest_idx != -1:
            repository = path[:digest_idx]
            reference = path[digest_idx:]  # includes "@"
        else:
            tag_idx = path.rfind(":")
            if tag_idx == -1:
                repository = path
                reference = None
            else:
                repository = path[:tag_idx]
                reference = path[tag_idx:]  # includes ":"

        if not repository:
            raise TypeError("Missing repository name in oci:// URL")

        # Optionally parse query params if you want (media types, annotations, etc.)
        query = parse_qs(str(parsed.query)) if parsed.query else {}

        return _OCIRequest(
            registry=registry,
            repository=repository,
            reference=reference,
            query=query,
            headers=request.headers,
            body=request.body or b"",
        )

    def do_get(self, request: _OCIRequest, response: ExtendedResponse):
        """
        Pull the artifact. Adapt to your client’s API. The goal is to return raw bytes or a file-like object.
        """
        logger.debug(f"Fetching data from: {request.ref}...")

        client: OrasClient = self._get_oras_with_optional_auth()

        try:
            data = client.pull(target=request.ref, outdir=self.outdir)

            if data:
                logger.debug(f"Data {data} successfully pulled from: {request.ref}")

                response.send_status(HTTPStatus.OK)

                pulled = Path(data[0])
                response.send_file_info(pulled)

                if pulled.is_file():
                    response.raw = io.open(pulled, __DEFAULT_READ_MODE__)
                    response.raw.release_conn = response.raw.close

                    response.send_header(
                        HTTPHeader.CONTENT_LENGTH, str(pulled.stat().st_size)
                    )
                else:
                    # TODO file listing
                    logger.warning("TODO: file listing is not supported yet")
                    response.send_status(HTTPStatus.NOT_IMPLEMENTED)
            else:
                response.send_status(HTTPStatus.NOT_FOUND)
        except ValueError as ve:
            logger.error(ve)

            if "Unauthorized" in ve.args[0]:
                response.send_status(HTTPStatus.UNAUTHORIZED)
            else:
                raise ve
        finally:
            self._logout(client)

    def do_head(self, request: _OCIRequest, response: ExtendedResponse):
        """
        Emulate HEAD via manifest lookup.
        """
        client: OrasClient = self._get_oras_with_optional_auth()

        try:
            manifest = getattr(client, "manifest", None) or getattr(
                client, "get_manifest", None
            )

            if manifest is None:
                # Fallback: try pull-without-download if your client supports it
                # Otherwise, we can attempt pull and discard
                client.pull(request.ref)
                # TODO no way to know the headers, here?!?
            else:
                meta = manifest(request.ref)
                # You can extract size/digest/mediaType if available to populate headers:
                if isinstance(meta, dict):
                    media_type = meta.get("mediaType") or meta.get("config", {}).get(
                        "mediaType"
                    )
                    if media_type:
                        response.headers[HTTPHeader.CONTENT_TYPE.name] = media_type

                    digest = meta.get("digest")
                    if digest:
                        response.headers["Docker-Content-Digest"] = digest

            response.send_status(HTTPStatus.OK)
        except Exception:
            response.send_status(HTTPStatus.NOT_FOUND)
        finally:
            self._logout(client)

    def do_put(self, request: _OCIRequest, response: ExtendedResponse):
        body = request.body
        if isinstance(request.body, str):
            body = body.encode(DEFAULT_ENCODING)

        # Guess media type if provided by caller
        media_type = (
            request.headers.get(HTTPHeader.ACCEPT.value)
            or ContentType.OCTET_STREAM.value
        )

        # Some clients accept: client.push(ref, data=..., media_type=...)
        # Others want: client.push(ref, files={"artifact": (name, bytes, media_type)})
        client: OrasClient = self._get_oras_with_optional_auth()
        try:
            # Adjust this call to your client’s signature:
            client.push(
                request.ref, data=body, media_type=media_type
            )  # <-- edit if needed
            response.send_status(HTTPStatus.CREATED)
        except TypeError:
            # Fallback: try a more generic signature
            try:
                client.push(request.ref, body)  # minimal signature
                response.send_status(HTTPStatus.CREATED)
            except AttributeError:
                response.send_error(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    "OrasClient does not have a compatible .push(...). Please adapt _oras_put().",
                )
        finally:
            self._logout(client)

    def do_delete(self, request: _OCIRequest, response: ExtendedResponse):
        """
        Delete by reference (if supported).
        """
        client: OrasClient = self._get_oras_with_optional_auth()
        try:
            delete_fn = getattr(client, "delete", None)
            if delete_fn:
                try:
                    delete_fn(request.ref)
                    response.send_status(HTTPStatus.NO_CONTENT)
                except Exception as e:
                    # Map some common errors if you can detect them
                    response.send_error(HTTPStatus.BAD_GATEWAY, e)
            else:
                response.send_error(
                    HTTPStatus.METHOD_NOT_ALLOWED,
                    "OrasClient does not have a compatible .delete(...). Please adapt _oras_delete().",
                )
        finally:
            self._logout(client)

    def close(self):
        pass
