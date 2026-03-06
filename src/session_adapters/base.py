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

from session_adapters.http_conts import (
    DEFAULT_ENCODING,
    ContentType,
    HTTPHeader,
    HTTPMethod,
)
from abc import abstractmethod
from http import HTTPStatus
from magic import Magic
from pathlib import Path
from requests import PreparedRequest, Response
from typing import Any, Dict, final, Generic, TypeVar, Union
from datetime import datetime

from requests.adapters import BaseAdapter

import mimetypes

__DEFAULT_READ_MODE__ = "rb"

__DATE_HEADER_FORMAT__ = "%a, %d %b %Y %H:%M:%S GMT"

AdapterRequest = TypeVar("AdapterRequest")

magic = Magic(mime=True, uncompress=True)

# Ensure YAML extensions are known by the stdlib
mimetypes.add_type(ContentType.YAML.value, ".yaml")
mimetypes.add_type(ContentType.YAML.value, ".yml")
mimetypes.add_type(ContentType.YAML.value, ".cwl")

# Optional: add other common texty types if you care
mimetypes.add_type(ContentType.JSON.value, ".json")
mimetypes.add_type(ContentType.XML.value, ".xml")


class ExtendedResponse(Response):
    def __init__(self):
        super().__init__()

    @final
    def send_status(self, http_status: HTTPStatus):
        self.status_code = http_status.value
        self.reason = http_status.phrase

    @final
    def send_header(self, name: Union[str, HTTPHeader], value: Any):
        self.headers[str(name)] = str(value)

    @final
    def send_date_header(self, name: Union[str, HTTPHeader], value: datetime):
        self.send_header(name=name, value=value.strftime(__DATE_HEADER_FORMAT__))

    @final
    def send_headers(self, headers_dict: Dict[HTTPHeader, Any]):
        if headers_dict:
            for key, value in headers_dict.items():
                self.send_header(name=key, value=value)

    @final
    def send_file_info(self, path: Path):
        stat_info = path.stat()
        mod_time_timestamp = stat_info.st_mtime
        mod_time = datetime.fromtimestamp(mod_time_timestamp)

        self.send_status(HTTPStatus.OK)
        self.send_date_header(HTTPHeader.LAST_MODIFIED, mod_time)

        mime = magic.from_file(path)
        if not mime or ContentType.PLAIN == ContentType(mime):
            guess_mime = mimetypes.guess_type(path)
            if guess_mime:
                mime = guess_mime[0]

        self.send_header(HTTPHeader.CONTENT_TYPE, mime)

    @final
    def send_error(self, http_status: HTTPStatus, error: Any):
        self.send_status(http_status)
        self._content = str(error).encode(DEFAULT_ENCODING)
        self.send_headers(
            {
                HTTPHeader.CONTENT_TYPE: ContentType.PLAIN,
                HTTPHeader.CONTENT_LENGTH: len(self._content),
            }
        )


class AbstractAdapter(BaseAdapter, Generic[AdapterRequest]):
    def __init__(self):
        super(AbstractAdapter, self).__init__()

        self.allowed_methods = ", ".join(
            list(
                map(
                    lambda method: method.name,
                    [
                        HTTPMethod.GET,
                        HTTPMethod.HEAD,
                        HTTPMethod.PUT,
                        HTTPMethod.DELETE,
                    ],
                )
            )
        )

    # ----- requests.Adapter API -----

    @final
    def send(
        self,
        request: PreparedRequest,
        stream=False,
        timeout=None,
        verify=True,
        cert=None,
        proxies=None,
    ) -> Response:
        """
        Map the PreparedRequest (s3://bucket/key) to a boto3 call and wrap the
        result into a requests.Response.
        """
        response = ExtendedResponse()
        response.url = (
            request.url if request.url else ""
        )  # should not happen, but IDE complains
        response.request = request
        response.send_date_header(HTTPHeader.DATE, datetime.now())

        try:
            parsed_request = self.parse_request(request=request)

            # Normalize method
            method = (
                HTTPMethod(request.method.upper()) if request.method else HTTPMethod.GET
            )  # should not happen

            match method:
                case HTTPMethod.GET:
                    self.do_get(request=parsed_request, response=response)

                case HTTPMethod.HEAD:
                    self.do_head(request=parsed_request, response=response)

                case HTTPMethod.PUT:
                    self.do_put(request=parsed_request, response=response)

                case HTTPMethod.DELETE:
                    self.do_delete(request=parsed_request, response=response)

                case _:
                    response.send_status(HTTPStatus.METHOD_NOT_ALLOWED)
                    response.send_header(HTTPHeader.ALLOW, self.allowed_methods)
        except ValueError as ve:
            response.send_error(HTTPStatus.METHOD_NOT_ALLOWED, ve)
        except TypeError as te:
            response.send_error(HTTPStatus.BAD_REQUEST, te)
        except Exception as e:
            response.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, e)

        return response

    @abstractmethod
    def parse_request(self, request: PreparedRequest) -> AdapterRequest:
        pass

    def do_head(self, request: AdapterRequest, response: ExtendedResponse):
        response.send_status(HTTPStatus.NOT_IMPLEMENTED)

    def do_get(self, request: AdapterRequest, response: ExtendedResponse):
        response.send_status(HTTPStatus.NOT_IMPLEMENTED)

    def do_put(self, request: AdapterRequest, response: ExtendedResponse):
        response.send_status(HTTPStatus.NOT_IMPLEMENTED)

    def do_delete(self, request: AdapterRequest, response: ExtendedResponse):
        response.send_status(HTTPStatus.NOT_IMPLEMENTED)
