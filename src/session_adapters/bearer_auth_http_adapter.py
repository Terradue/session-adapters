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

from requests import PreparedRequest, Response
from requests.adapters import HTTPAdapter


class BearerAuthHTTPAdapter(HTTPAdapter):
    def __init__(self, token: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.token = token

    def send(
        self,
        request: PreparedRequest,
        *args,
        **kwargs,
    ) -> Response:
        request.headers["Authorization"] = f"Bearer {self.token}"
        return super().send(request, *args, **kwargs)
