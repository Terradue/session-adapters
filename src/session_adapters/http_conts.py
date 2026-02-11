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

from enum import (
    auto,
    Enum
)

DEFAULT_ENCODING = 'utf-8'

class HTTPMethod(Enum):
    """
    A comprehensive Enum of HTTP methods.
    """
    @staticmethod
    def _generate_next_value_(name, start, count, last_values):
        return name  # ensures auto() = member name as string

    GET = auto()
    HEAD = auto()
    PUT = auto()
    DELETE = auto()
    POST = auto()
    OPTIONS = auto()
    PATCH = auto()
    CONNECT = auto()
    TRACE = auto()

    def __str__(self) -> str:
        return self.name

class HTTPHeader(str, Enum):
    """
    A comprehensive Enum of HTTP header names, modeled after common fields from
    IANA’s HTTP Field Name Registry and de-facto headers used on the web.

    Usage:
        from http_headers import HttpHeader
        headers = {HttpHeader.CONTENT_TYPE: "application/json"}
    """
    # --- Request headers ---
    A_IM = "A-IM"
    ACCEPT = "Accept"
    ACCEPT_CH = "Accept-CH"
    ACCEPT_CH_LIFETIME = "Accept-CH-Lifetime"
    ACCEPT_ENCODING = "Accept-Encoding"
    ACCEPT_LANGUAGE = "Accept-Language"
    ACCEPT_PATCH = "Accept-Patch"
    ACCEPT_POST = "Accept-Post"
    ACCEPT_RANGES = "Accept-Ranges"
    ACCEPT_SIGNATURE = "Accept-Signature"  # draft/non-standard in many stacks
    ACCESS_CONTROL_REQUEST_HEADERS = "Access-Control-Request-Headers"
    ACCESS_CONTROL_REQUEST_METHOD = "Access-Control-Request-Method"
    AUTHORIZATION = "Authorization"
    CACHE_CONTROL = "Cache-Control"
    CONNECTION = "Connection"
    CONTENT_LENGTH = "Content-Length"
    CONTENT_TYPE = "Content-Type"
    COOKIE = "Cookie"
    DATE = "Date"
    DEVICE_MEMORY = "Device-Memory"  # Client Hints
    DNT = "DNT"
    DPR = "DPR"  # Client Hints
    EARLY_DATA = "Early-Data"
    EXPECT = "Expect"
    FORWARDED = "Forwarded"
    FROM = "From"
    HOST = "Host"
    IF_MATCH = "If-Match"
    IF_MODIFIED_SINCE = "If-Modified-Since"
    IF_NONE_MATCH = "If-None-Match"
    IF_RANGE = "If-Range"
    IF_UNMODIFIED_SINCE = "If-Unmodified-Since"
    KEEP_ALIVE = "Keep-Alive"
    MAX_FORWARDS = "Max-Forwards"
    ORIGIN = "Origin"
    PERMISSIONS_POLICY = "Permissions-Policy"  # formerly Feature-Policy
    PRAGMA = "Pragma"
    PRIORITY = "Priority"
    PROXY_AUTHORIZATION = "Proxy-Authorization"
    RANGE = "Range"
    REFERER = "Referer"
    REFERRER_POLICY = "Referrer-Policy"
    SAVE_DATA = "Save-Data"  # Client Hint
    SEC_CH_UA = "Sec-CH-UA"
    SEC_CH_UA_ARCH = "Sec-CH-UA-Arch"
    SEC_CH_UA_BITNESS = "Sec-CH-UA-Bitness"
    SEC_CH_UA_FULL_VERSION = "Sec-CH-UA-Full-Version"
    SEC_CH_UA_FULL_VERSION_LIST = "Sec-CH-UA-Full-Version-List"
    SEC_CH_UA_MOBILE = "Sec-CH-UA-Mobile"
    SEC_CH_UA_MODEL = "Sec-CH-UA-Model"
    SEC_CH_UA_PLATFORM = "Sec-CH-UA-Platform"
    SEC_CH_UA_PLATFORM_VERSION = "Sec-CH-UA-Platform-Version"
    SEC_FETCH_DEST = "Sec-Fetch-Dest"
    SEC_FETCH_MODE = "Sec-Fetch-Mode"
    SEC_FETCH_SITE = "Sec-Fetch-Site"
    SEC_FETCH_USER = "Sec-Fetch-User"
    SEC_GPC = "Sec-GPC"
    SEC_PURPOSE = "Sec-Purpose"
    TE = "TE"
    TRAILER = "Trailer"
    TRANSFER_ENCODING = "Transfer-Encoding"
    UPGRADE = "Upgrade"
    UPGRADE_INSECURE_REQUESTS = "Upgrade-Insecure-Requests"
    USER_AGENT = "User-Agent"
    VIA = "Via"
    VIEWPORT_WIDTH = "Viewport-Width"  # Client Hints
    WIDTH = "Width"  # Client Hints

    # --- Response headers ---
    ACCEPT_RANGES_RESP = "Accept-Ranges"
    ACCESS_CONTROL_ALLOW_CREDENTIALS = "Access-Control-Allow-Credentials"
    ACCESS_CONTROL_ALLOW_HEADERS = "Access-Control-Allow-Headers"
    ACCESS_CONTROL_ALLOW_METHODS = "Access-Control-Allow-Methods"
    ACCESS_CONTROL_ALLOW_ORIGIN = "Access-Control-Allow-Origin"
    ACCESS_CONTROL_EXPOSE_HEADERS = "Access-Control-Expose-Headers"
    ACCESS_CONTROL_MAX_AGE = "Access-Control-Max-Age"
    AGE = "Age"
    ALLOW = "Allow"
    ALT_SVC = "Alt-Svc"
    ALT_USED = "Alt-Used"
    CONTENT_DISPOSITION = "Content-Disposition"
    CONTENT_ENCODING = "Content-Encoding"
    CONTENT_LANGUAGE = "Content-Language"
    CONTENT_LOCATION = "Content-Location"
    CONTENT_RANGE = "Content-Range"
    CONTENT_SECURITY_POLICY = "Content-Security-Policy"
    CONTENT_SECURITY_POLICY_REPORT_ONLY = "Content-Security-Policy-Report-Only"
    ETAG = "ETag"
    EXPIRES = "Expires"
    LAST_MODIFIED = "Last-Modified"
    LINK = "Link"
    LOCATION = "Location"
    NEL = "NEL"
    PROXY_AUTHENTICATE = "Proxy-Authenticate"
    REPORT_TO = "Report-To"  # deprecated in favor of Reporting-Endpoints
    REPORTING_ENDPOINTS = "Reporting-Endpoints"
    RETRY_AFTER = "Retry-After"
    SERVER = "Server"
    SERVER_TIMING = "Server-Timing"
    SET_COOKIE = "Set-Cookie"
    SOURCE_MAP = "SourceMap"
    STRICT_TRANSPORT_SECURITY = "Strict-Transport-Security"
    TIMING_ALLOW_ORIGIN = "Timing-Allow-Origin"
    VARY = "Vary"
    WWW_AUTHENTICATE = "WWW-Authenticate"
    X_CONTENT_TYPE_OPTIONS = "X-Content-Type-Options"
    X_DNS_PREFETCH_CONTROL = "X-DNS-Prefetch-Control"
    X_FRAME_OPTIONS = "X-Frame-Options"
    X_PERMITTED_CROSS_DOMAIN_POLICIES = "X-Permitted-Cross-Domain-Policies"
    X_POWERED_BY = "X-Powered-By"
    X_REQUEST_ID = "X-Request-Id"
    X_RESPONSE_TIME = "X-Response-Time"
    X_XSS_PROTECTION = "X-XSS-Protection"
    X_FORWARDED_FOR = "X-Forwarded-For"
    X_FORWARDED_HOST = "X-Forwarded-Host"
    X_FORWARDED_PROTO = "X-Forwarded-Proto"

    # --- Common both-sides / misc ---
    CONTENT_MD5 = "Content-MD5"  # non-standard but seen
    EXPECT_CT = "Expect-CT"  # largely deprecated
    # HTTP Message Signatures (RFC 9421)
    SIGNATURE = "Signature"
    SIGNATURE_INPUT = "Signature-Input"
    # HTTP Representation Digest (RFC 9530)
    CONTENT_DIGEST = "Content-Digest"
    REPR_DIGEST = "Repr-Digest"

    # Cloud/CDN/observability (non-standard but widely used)
    CF_CACHE_STATUS = "CF-Cache-Status"
    CF_RAY = "CF-RAY"
    CDN_CACHE_CONTROL = "CDN-Cache-Control"
    FLY_REQUEST_ID = "Fly-Request-Id"
    X_AMZN_TRACE_ID = "X-Amzn-Trace-Id"
    X_AZURE_REF = "X-Azure-Ref"
    X_CACHE = "X-Cache"
    X_CACHE_HIT = "X-Cache-Hit"
    X_CORRELATION_ID = "X-Correlation-ID"
    X_REQUESTED_WITH = "X-Requested-With"

    # Security / COOP/COEP/CORP
    CROSS_ORIGIN_EMBEDDER_POLICY = "Cross-Origin-Embedder-Policy"
    CROSS_ORIGIN_OPENER_POLICY = "Cross-Origin-Opener-Policy"
    CROSS_ORIGIN_RESOURCE_POLICY = "Cross-Origin-Resource-Policy"

    def __str__(self) -> str:
        return self.value

# Convenience: a frozenset of canonical "entity" headers
ENTITY_HEADER_SET = frozenset({
    HTTPHeader.CONTENT_TYPE,
    HTTPHeader.CONTENT_LENGTH,
    HTTPHeader.CONTENT_ENCODING,
    HTTPHeader.CONTENT_LANGUAGE,
    HTTPHeader.CONTENT_DISPOSITION,
    HTTPHeader.CONTENT_LOCATION,
    HTTPHeader.CONTENT_RANGE,
    HTTPHeader.CONTENT_MD5,
    HTTPHeader.CONTENT_DIGEST,
})

class ContentType(str, Enum):
    # --- Text ---
    PLAIN = "text/plain"
    HTML = "text/html"
    CSS = "text/css"
    CSV = "text/csv"
    TEXT_JAVASCRIPT = "text/javascript"
    MARKDOWN = "text/markdown"
    XML_TEXT = "text/xml"

    # --- Application / structured text ---
    JSON = "application/json"
    PROBLEM_JSON = "application/problem+json"
    SCHEMA_JSON = "application/schema+json"
    XML = "application/xml"
    YAML = "application/x-yaml"
    FORM_URLENCODED = "application/x-www-form-urlencoded"
    OCTET_STREAM = "application/octet-stream"
    PDF = "application/pdf"
    ZIP = "application/zip"
    GZIP = "application/gzip"
    TAR = "application/x-tar"
    RTF = "application/rtf"
    APPLICATION_JAVASCRIPT = "application/javascript"

    # --- Multipart ---
    MULTIPART_FORM = "multipart/form-data"
    MULTIPART_MIXED = "multipart/mixed"
    MULTIPART_ALTERNATIVE = "multipart/alternative"
    MULTIPART_RELATED = "multipart/related"

    # --- Images ---
    JPEG = "image/jpeg"
    PNG = "image/png"
    GIF = "image/gif"
    WEBP = "image/webp"
    SVG = "image/svg+xml"
    TIFF = "image/tiff"
    BMP = "image/bmp"
    ICON = "image/x-icon"

    # --- Audio ---
    MP3 = "audio/mpeg"
    OGG = "audio/ogg"
    WAV = "audio/wav"
    WEBM_AUDIO = "audio/webm"

    # --- Video ---
    MP4 = "video/mp4"
    MPEG = "video/mpeg"
    OGG_VIDEO = "video/ogg"
    WEBM_VIDEO = "video/webm"
    QUICKTIME = "video/quicktime"

    # --- Fonts ---
    WOFF = "font/woff"
    WOFF2 = "font/woff2"
    TTF = "font/ttf"
    OTF = "font/otf"

    # --- Misc / Special ---
    ANY = "*/*"

    def __str__(self) -> str:
        return self.value
