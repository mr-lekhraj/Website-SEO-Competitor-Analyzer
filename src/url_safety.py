"""SSRF-resistant public URL fetching for website audits and competitor snapshots.

Requests are pinned to a validated public IP address. The original hostname is
kept in the URL so HTTP Host headers and HTTPS certificate/SNI checks remain
correct. Redirect targets are validated and resolved independently.
"""
from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import socket
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
from requests.adapters import HTTPAdapter
from urllib3 import PoolManager
from urllib3.poolmanager import pool_classes_by_scheme
from urllib3.connection import HTTPConnection, HTTPSConnection
from urllib3.connectionpool import HTTPConnectionPool, HTTPSConnectionPool
from urllib3.exceptions import NewConnectionError
from urllib3.util import connection as urllib3_connection


DEFAULT_TIMEOUT = (5, 15)
DEFAULT_MAX_BYTES = 2 * 1024 * 1024
DEFAULT_MAX_REDIRECTS = 5
_REDIRECT_CODES = {301, 302, 303, 307, 308}
_BLOCKED_SUFFIXES = (
    ".localhost", ".local", ".internal", ".home", ".test", ".invalid", ".example"
)


class URLSafetyError(ValueError):
    """Raised when a URL is not safe to fetch from the public internet."""


@dataclass(frozen=True)
class SafeResponse:
    """Small response object containing only the bounded body we actually read."""

    url: str
    status_code: int
    headers: dict
    content: bytes


def _public_ip(value: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    try:
        address = ipaddress.ip_address(value.split("%", 1)[0])
    except ValueError as exc:
        raise URLSafetyError("The URL host did not resolve to a valid IP address.") from exc
    if not address.is_global:
        raise URLSafetyError("The URL resolves to a non-public or reserved IP address.")
    return address


def _normalize_and_resolve(url: str) -> tuple[str, str, int, str]:
    """Validate a URL and return (normalized URL, host, port, pinned public IP)."""
    if not isinstance(url, str) or not url.strip():
        raise URLSafetyError("Enter a valid website URL.")

    try:
        parsed = urlsplit(url.strip())
        scheme = parsed.scheme.lower()
        if scheme not in {"http", "https"}:
            raise URLSafetyError("Only http:// and https:// website URLs are allowed.")
        if not parsed.netloc or parsed.username is not None or parsed.password is not None:
            raise URLSafetyError("The URL must contain a hostname and cannot contain credentials.")
        host = parsed.hostname
        explicit_port = parsed.port
    except ValueError as exc:
        raise URLSafetyError("The website URL is malformed.") from exc

    if not host or any(ord(char) < 33 for char in host):
        raise URLSafetyError("The URL hostname is invalid.")

    # Only standard web ports are supported; this blocks access to arbitrary
    # services exposed on otherwise public hosts.
    default_port = 443 if scheme == "https" else 80
    if explicit_port is not None and explicit_port != default_port:
        raise URLSafetyError("Only standard HTTP (80) and HTTPS (443) ports are allowed.")
    port = default_port

    if "%" in host:
        raise URLSafetyError("Scoped or encoded IP hostnames are not allowed.")

    try:
        literal_ip = ipaddress.ip_address(host)
    except ValueError:
        literal_ip = None

    if literal_ip is not None:
        _public_ip(str(literal_ip))
        pinned_ip = str(literal_ip)
        normalized_host = f"[{host}]" if literal_ip.version == 6 else host
    else:
        # Do not reinterpret malformed numeric IPv4 forms as DNS names.
        if all(char.isdigit() or char == "." for char in host):
            raise URLSafetyError("The IP address in the URL is invalid or not public.")
        try:
            ascii_host = host.rstrip(".").encode("idna").decode("ascii").lower()
        except UnicodeError as exc:
            raise URLSafetyError("The URL hostname is invalid.") from exc
        if (
            not ascii_host
            or ascii_host == "localhost"
            or ascii_host.endswith(_BLOCKED_SUFFIXES)
        ):
            raise URLSafetyError("Local and reserved hostnames cannot be fetched.")

        try:
            records = socket.getaddrinfo(ascii_host, port, type=socket.SOCK_STREAM)
        except OSError as exc:
            raise URLSafetyError("The website hostname could not be resolved.") from exc
        addresses = []
        for record in records:
            address = _public_ip(record[4][0])
            if str(address) not in addresses:
                addresses.append(str(address))
        if not addresses:
            raise URLSafetyError("The website hostname has no usable public IP address.")
        # Reject mixed public/private DNS answers; choose one validated public
        # address and pin the underlying socket to it to prevent DNS rebinding.
        pinned_ip = addresses[0]
        normalized_host = ascii_host

    netloc = normalized_host
    normalized_url = urlunsplit((
        scheme,
        netloc,
        parsed.path or "/",
        parsed.query,
        "",  # URL fragments are never sent to the server.
    ))
    return normalized_url, host, port, pinned_ip


class _PinnedConnectionMixin:
    """Connect to a validated IP while retaining the URL hostname for TLS."""

    def __init__(self, *args, pinned_ip: str | None = None, **kwargs):
        self._pinned_ip = pinned_ip
        if not self._pinned_ip:
            raise ValueError("A validated destination IP is required.")
        super().__init__(*args, **kwargs)

    def _new_conn(self):
        try:
            return urllib3_connection.create_connection(
                (self._pinned_ip, self.port),
                self.timeout,
                source_address=self.source_address,
                socket_options=self.socket_options,
            )
        except OSError as exc:
            raise NewConnectionError(
                self, f"Could not connect to validated public address {self._pinned_ip}: {exc}"
            ) from exc


class _PinnedHTTPConnection(_PinnedConnectionMixin, HTTPConnection):
    pass


class _PinnedHTTPSConnection(_PinnedConnectionMixin, HTTPSConnection):
    pass


class _PinnedHTTPConnectionPool(HTTPConnectionPool):
    ConnectionCls = _PinnedHTTPConnection


class _PinnedHTTPSConnectionPool(HTTPSConnectionPool):
    ConnectionCls = _PinnedHTTPSConnection


class _PinnedPoolManager(PoolManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # PoolManager.__init__ assigns the module defaults to each instance,
        # so install our custom connection pools after calling super().
        self.pool_classes_by_scheme = {
            **self.pool_classes_by_scheme,
            "http": _PinnedHTTPConnectionPool,
            "https": _PinnedHTTPSConnectionPool,
        }

    def connection_from_context(self, request_context):
        # pinned_ip is required when constructing a connection pool, but it is
        # not a PoolKey field. Exclude it only from the cache key while keeping
        # it in the original context passed to _new_pool().
        key_context = request_context.copy()
        key_context.pop("pinned_ip", None)
        scheme = key_context["scheme"].lower()
        key_constructor = self.key_fn_by_scheme.get(scheme)
        if key_constructor is None:
            raise ValueError(f"Unsupported URL scheme: {scheme}")
        pool_key = key_constructor(key_context)
        return self.connection_from_pool_key(pool_key, request_context=request_context)


class _PinnedHTTPAdapter(HTTPAdapter):
    def __init__(self, pinned_ip: str):
        self._pinned_ip = pinned_ip
        super().__init__(max_retries=0)

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        pool_kwargs["pinned_ip"] = self._pinned_ip
        self.poolmanager = _PinnedPoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            **pool_kwargs,
        )


def validate_public_url(url: str) -> str:
    """Return a normalized URL only when its destination resolves publicly."""
    normalized, _, _, _ = _normalize_and_resolve(url)
    return normalized


def safe_fetch(
    url: str,
    *,
    headers: dict | None = None,
    timeout: tuple[float, float] = DEFAULT_TIMEOUT,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_redirects: int = DEFAULT_MAX_REDIRECTS,
) -> SafeResponse:
    """Fetch a public web page with DNS pinning, redirect checks and body limits."""
    if max_bytes < 1:
        raise ValueError("max_bytes must be at least 1.")
    if max_redirects < 0:
        raise ValueError("max_redirects cannot be negative.")

    current_url = url
    for redirect_count in range(max_redirects + 1):
        normalized_url, _, _, pinned_ip = _normalize_and_resolve(current_url)
        session = requests.Session()
        session.trust_env = False  # Do not inherit proxy settings from the host.
        adapter = _PinnedHTTPAdapter(pinned_ip)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        try:
            with session.get(
                normalized_url,
                headers=headers or {},
                timeout=timeout,
                allow_redirects=False,
                stream=True,
                verify=True,
            ) as response:
                if response.status_code in _REDIRECT_CODES:
                    location = response.headers.get("Location")
                    if not location:
                        raise URLSafetyError("The website returned a redirect without a destination.")
                    if redirect_count >= max_redirects:
                        raise URLSafetyError("The website exceeded the allowed redirect limit.")
                    current_url = urljoin(normalized_url, location)
                    continue

                content_length = response.headers.get("Content-Length")
                if content_length:
                    try:
                        declared_size = int(content_length)
                    except ValueError:
                        declared_size = None
                    if declared_size is not None and declared_size > max_bytes:
                        raise URLSafetyError("The web page exceeds the allowed response size.")

                body = bytearray()
                for chunk in response.iter_content(chunk_size=65536):
                    if not chunk:
                        continue
                    body.extend(chunk)
                    if len(body) > max_bytes:
                        raise URLSafetyError("The web page exceeds the allowed response size.")

                return SafeResponse(
                    url=normalized_url,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    content=bytes(body),
                )
        finally:
            session.close()

    raise URLSafetyError("The website exceeded the allowed redirect limit.")
