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
from session_adapters.http_conts import HTTPHeader
from http import HTTPStatus
from loguru import logger
from pathlib import Path
from pydantic import BaseModel
from shutil import rmtree
from requests import PreparedRequest
from urllib.parse import urlparse
from typing import Any, final

import errno
import io

import os

__DEFAULT_WRITE_MODE__ = "w"


class _FileRequest(BaseModel):
    path: Path
    # from original request
    body: Any


@final
class FileAdapter(AbstractAdapter[_FileRequest]):
    def __init__(self):
        super(FileAdapter, self).__init__()

    def parse_request(self, request: PreparedRequest) -> _FileRequest:
        url_parts = urlparse(request.url)

        if url_parts.netloc and url_parts.netloc != "localhost":
            raise TypeError(
                "URLs with hostname components are not allowed, 'localhost' supported only"
            )

        return _FileRequest(path=Path(str(url_parts.path)), body=request.body or b"")

    def do_head(self, request: _FileRequest, response: ExtendedResponse):
        try:
            if request.path.exists():
                response.send_file_info(request.path)
            else:
                response.send_error(
                    HTTPStatus.NOT_FOUND,
                    f"File {request.path} does not exist on the local File System",
                )
        except IOError as ioe:
            match ioe.errno:
                case errno.EACCES:
                    response.send_error(HTTPStatus.FORBIDDEN, ioe)

                case errno.ENOENT:
                    response.send_error(HTTPStatus.NOT_FOUND, ioe)

                case _:
                    response.send_error(HTTPStatus.BAD_REQUEST, ioe)

    def do_get(self, request: _FileRequest, response: ExtendedResponse):
        try:
            if request.path.exists():
                response.send_file_info(request.path)

                if request.path.is_file():
                    response.raw = io.open(request.path, __DEFAULT_READ_MODE__)
                    response.raw.release_conn = response.raw.close

                    response.send_header(
                        HTTPHeader.CONTENT_LENGTH, str(request.path.stat().st_size)
                    )
                else:
                    # TODO file listing
                    logger.warning("TODO: file listing is not supported yet")
                    response.send_status(HTTPStatus.NOT_IMPLEMENTED)
            else:
                response.send_error(
                    HTTPStatus.NOT_FOUND,
                    f"File {request.path} does not exist on the local File System",
                )
        except IOError as ioe:
            match ioe.errno:
                case errno.EACCES:
                    response.send_error(HTTPStatus.FORBIDDEN, ioe)

                case errno.ENOENT:
                    response.send_error(HTTPStatus.NOT_FOUND, ioe)

                case _:
                    response.send_error(HTTPStatus.BAD_REQUEST, ioe)

    def do_delete(self, request: _FileRequest, response: ExtendedResponse):
        self.do_head(request, response)

        try:
            if request.path.exists():
                if request.path.is_dir():
                    rmtree(request.path.absolute())
                elif request.path.is_file():
                    os.remove(request.path.absolute())
        except IOError:
            pass

    def do_put(self, request: _FileRequest, response: ExtendedResponse):
        request.path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with request.path.open(__DEFAULT_WRITE_MODE__) as f:
                f.write(request.body)
        except IOError as ioe:
            response.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, ioe)

    def close(self):
        # No persistent sockets to close beyond what botocore manages, but keep hook for API parity.
        pass
