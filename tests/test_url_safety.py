import socket

import pytest

from src import url_safety


PUBLIC_DNS = [
    (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))
]


def test_blocks_private_and_reserved_ip_literals():
    for url in (
        "http://127.0.0.1/",
        "http://10.0.0.5/",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]/",
        "http://192.168.1.10/",
    ):
        with pytest.raises(url_safety.URLSafetyError):
            url_safety.validate_public_url(url)


def test_blocks_local_hostnames_without_dns_lookup(monkeypatch):
    def unexpected_lookup(*args, **kwargs):
        raise AssertionError("Local hostnames should be rejected before DNS lookup.")

    monkeypatch.setattr(url_safety.socket, "getaddrinfo", unexpected_lookup)
    for host in ("localhost", "printer.local", "service.internal", "test.example"):
        with pytest.raises(url_safety.URLSafetyError):
            url_safety.validate_public_url(f"https://{host}/")


def test_rejects_hostname_with_any_non_public_dns_answer(monkeypatch):
    answers = PUBLIC_DNS + [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.7", 443))
    ]
    monkeypatch.setattr(url_safety.socket, "getaddrinfo", lambda *a, **k: answers)
    with pytest.raises(url_safety.URLSafetyError, match="non-public"):
        url_safety.validate_public_url("https://mixed.example/")


def test_rejects_non_web_ports_credentials_and_non_http_schemes():
    candidates = (
        "http://public.example:8080/",
        "https://user:pass@public.example/",
        "file:///etc/passwd",
        "javascript:alert(1)",
    )
    for url in candidates:
        with pytest.raises(url_safety.URLSafetyError):
            url_safety.validate_public_url(url)


def test_dns_hostname_is_normalized_and_resolved(monkeypatch):
    monkeypatch.setattr(url_safety.socket, "getaddrinfo", lambda *a, **k: PUBLIC_DNS)
    normalized = url_safety.validate_public_url("HTTPS://Example.COM/path#fragment")
    assert normalized == "https://example.com/path"


def test_http_connection_uses_pinned_ip(monkeypatch):
    destinations = []

    class DummySocket:
        def close(self):
            pass

    def fake_create_connection(address, timeout, source_address=None, socket_options=None):
        destinations.append(address)
        return DummySocket()

    monkeypatch.setattr(url_safety.urllib3_connection, "create_connection", fake_create_connection)
    connection = url_safety._PinnedHTTPConnection(
        host="public.example", port=80, pinned_ip="8.8.8.8", timeout=3
    )
    connection._new_conn()
    assert destinations == [("8.8.8.8", 80)]


def test_redirect_to_private_ip_is_blocked_before_second_request(monkeypatch):
    monkeypatch.setattr(url_safety.socket, "getaddrinfo", lambda *a, **k: PUBLIC_DNS)
    requests_made = []

    class FakeResponse:
        status_code = 302
        headers = {"Location": "http://127.0.0.1/admin"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def iter_content(self, chunk_size):
            return iter(())

    class FakeSession:
        def __init__(self):
            self.trust_env = True
            self.calls = []

        def mount(self, *args):
            pass

        def get(self, url, **kwargs):
            self.calls.append((url, kwargs))
            requests_made.append(url)
            return FakeResponse()

        def close(self):
            pass

    monkeypatch.setattr(url_safety.requests, "Session", FakeSession)
    with pytest.raises(url_safety.URLSafetyError):
        url_safety.safe_fetch("https://public.example/start")
    assert requests_made == ["https://public.example/start"]


def test_safe_fetch_enforces_body_limit(monkeypatch):
    monkeypatch.setattr(url_safety.socket, "getaddrinfo", lambda *a, **k: PUBLIC_DNS)

    class FakeResponse:
        status_code = 200
        headers = {"Content-Length": "10"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def iter_content(self, chunk_size):
            return iter((b"0123456789",))

    class FakeSession:
        def __init__(self):
            self.trust_env = True

        def mount(self, *args):
            pass

        def get(self, url, **kwargs):
            assert kwargs["allow_redirects"] is False
            assert kwargs["stream"] is True
            return FakeResponse()

        def close(self):
            pass

    monkeypatch.setattr(url_safety.requests, "Session", FakeSession)
    with pytest.raises(url_safety.URLSafetyError, match="response size"):
        url_safety.safe_fetch("https://public.example/", max_bytes=5)
