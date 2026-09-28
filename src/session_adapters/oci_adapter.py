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

from http import HTTPStatus
from pathlib import Path
from typing import Any, final
from urllib.parse import parse_qs, urlparse

from docker.auth import AuthConfig  # type: ignore[import-untyped]
from docker.auth import load_config as load_auth_config
from loguru import logger
from oras.client import OrasClient  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, computed_field
from requests import PreparedRequest
from requests.structures import CaseInsensitiveDict

from session_adapters.base import (
    __DEFAULT_READ_MODE__,
    AbstractAdapter,
    ExtendedResponse,
)
from session_adapters.conainers_auth import ContainersAuth
from session_adapters.http_conts import DEFAULT_ENCODING, ContentType, HTTPHeader

OCI_SCHEME = "oci://"


class _OCIRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    registry: str
    repository: str
    reference: str | None = None
    query: dict[str, list[str]]
    # from original request
    headers: CaseInsensitiveDict[str | bytes]
    body: Any

    @computed_field  # type: ignore[prop-decorator]
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

    Credentials are selected from the container auth configuration for each request.
    """

    def __init__(
        self,
        containers_auth: ContainersAuth | None = None,
        outdir: str | None = None,
    ) -> None:
        super().__init__()

        containers_auth = containers_auth or ContainersAuth(auths={})
        self.auth_config: AuthConfig = load_auth_config(
            config_dict={
                "auths": {},
                **containers_auth.model_dump(mode="json", by_alias=True, exclude_none=True),
            }
        )
        self.outdir = outdir

    def _resolve_request_auth(self, request: _OCIRequest) -> dict[str, Any] | None:
        # Docker's resolver strips paths from keys. Filter first so credentials
        # for a sibling namespace can never become registry-wide credentials.
        auths = {}
        for key, value in self.auth_config.auths.items():
            normalized = key
            # Bare host:port keys must not be interpreted as URL schemes.
            if "://" in key:
                parsed = urlparse(key)
                normalized = f"{parsed.netloc}{parsed.path}"
            auths[normalized.rstrip("/")] = value
        scope = f"{request.registry}/{request.repository}"
        selected = {}
        while scope:
            if scope in auths:
                selected = {request.registry: auths[scope]}
                break
            scope = scope.rpartition("/")[0]

        contextual_config = AuthConfig(
            {
                "auths": selected,
                "credHelpers": self.auth_config.cred_helpers,
                "credsStore": self.auth_config.creds_store,
            }
        )
        # AuthConfig delegates helper execution and missing-credential handling
        # to docker.credentials.Store.
        return contextual_config.resolve_authconfig(request.registry)  # type: ignore[no-any-return]

    def _get_oras_with_optional_auth(self, request: _OCIRequest) -> OrasClient:
        client = None
        try:
            auth = self._resolve_request_auth(request) or {}
            username = auth.get("username") or auth.get("Username")
            password = auth.get("password") or auth.get("Password")
            if username and password:
                client = OrasClient(hostname=request.registry)
                client.login(username=username, password=password, hostname=request.registry)
                return client
        except Exception:
            # Helper errors can contain secrets; do not include their text.
            logger.warning("OCI login/auth handshake failed -> retry anonymously")
            if client is not None:
                self._logout(client)

        return OrasClient()

    def _logout(self, client: OrasClient) -> None:
        hosts = set(client.auth._auth_config.get("auths", {}))
        if client.hostname:
            hosts.add(client.hostname)
        try:
            for hostname in hosts:
                try:
                    client.logout(hostname)
                except Exception:  # noqa: PERF203 - attempt every logout even after a failure
                    logger.warning("OCI logout failed")
        finally:
            client.session.close()

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

    def do_get(self, request: _OCIRequest, response: ExtendedResponse) -> None:
        """
        Pull the artifact. Adapt to your client's API. The goal is to return raw bytes or a file-like object.
        """
        logger.debug(f"Fetching data from: {request.ref}...")

        client: OrasClient = self._get_oras_with_optional_auth(request)

        try:
            data = client.pull(target=request.ref, outdir=self.outdir)

            if data:
                logger.debug(f"Data {data} successfully pulled from: {request.ref}")

                response.send_status(HTTPStatus.OK)

                pulled = Path(data[0])
                response.send_file_info(pulled)

                if pulled.is_file():
                    # The response owns this stream and closes it after consumption.
                    response.raw = pulled.open(__DEFAULT_READ_MODE__)
                    response.raw.release_conn = response.raw.close

                    response.send_header(HTTPHeader.CONTENT_LENGTH, str(pulled.stat().st_size))
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

    def do_head(self, request: _OCIRequest, response: ExtendedResponse) -> None:
        """
        Emulate HEAD via manifest lookup.
        """
        client: OrasClient = self._get_oras_with_optional_auth(request)

        try:
            manifest = getattr(client, "manifest", None) or getattr(client, "get_manifest", None)

            if manifest is None:
                # Fallback: try pull-without-download if your client supports it
                # Otherwise, we can attempt pull and discard
                client.pull(request.ref)
                # TODO no way to know the headers, here?!?
            else:
                meta = manifest(request.ref)
                # You can extract size/digest/mediaType if available to populate headers:
                if isinstance(meta, dict):
                    media_type = meta.get("mediaType") or meta.get("config", {}).get("mediaType")
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

    def do_put(self, request: _OCIRequest, response: ExtendedResponse) -> None:
        body = request.body
        if isinstance(request.body, str):
            body = body.encode(DEFAULT_ENCODING)

        # Guess media type if provided by caller
        media_type = request.headers.get(HTTPHeader.ACCEPT.value) or ContentType.OCTET_STREAM.value

        # Some clients accept: client.push(ref, data=..., media_type=...)
        # Others want: client.push(ref, files={"artifact": (name, bytes, media_type)})
        client: OrasClient = self._get_oras_with_optional_auth(request)
        try:
            # Adjust this call to your client's signature:
            client.push(request.ref, data=body, media_type=media_type)  # <-- edit if needed
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

    def do_delete(self, request: _OCIRequest, response: ExtendedResponse) -> None:
        """
        Delete by reference (if supported).
        """
        client: OrasClient = self._get_oras_with_optional_auth(request)
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

    def close(self) -> None:
        pass
