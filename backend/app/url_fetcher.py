"""SSRF-safe retrieval of text job postings from public HTTP(S) URLs."""

import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import httpx


class URLFetchError(Exception):
    """Base class for expected URL retrieval failures."""


class InvalidURL(URLFetchError):
    """The URL is malformed or targets a disallowed network address."""


class URLFetchTooLarge(URLFetchError):
    """The response exceeds the configured byte limit."""


class URLFetchUnsupportedContent(URLFetchError):
    """The response content type is not supported for text extraction."""


class URLFetchTimeout(URLFetchError):
    """The remote server did not respond within the configured timeout."""


class URLFetchUpstreamError(URLFetchError):
    """The upstream request failed or returned an unusable response."""


@dataclass(frozen=True)
class FetchedText:
    """Text and final URL returned by a bounded fetch."""

    text: str
    final_url: str
    content_type: str


ALLOWED_SCHEMES = {"http", "https"}
ALLOWED_CONTENT_TYPES = {
    "text/html",
    "text/plain",
    "application/xhtml+xml",
}


def _is_blocked_address(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        address.is_private
        or address.is_link_local
        or address.is_loopback
        or address.is_unspecified
        or address.is_multicast
        or address.is_reserved
    )


async def _resolve_public_addresses(hostname: str, port: int) -> None:
    """Resolve all addresses and reject a host if any result is non-public."""
    try:
        addresses = await asyncio.to_thread(
            socket.getaddrinfo,
            hostname,
            port,
            type=socket.SOCK_STREAM,
        )
    except (OSError, UnicodeError) as exc:
        raise InvalidURL("The URL host could not be resolved.") from exc

    if not addresses:
        raise InvalidURL("The URL host did not resolve to an address.")

    for address_info in addresses:
        try:
            address = ipaddress.ip_address(address_info[4][0])
        except ValueError as exc:
            raise InvalidURL("The URL host resolved to an invalid address.") from exc
        if _is_blocked_address(address):
            raise InvalidURL("URLs targeting private or local network addresses are not allowed.")


async def validate_url(url: str) -> str:
    """Validate a URL and its resolved addresses before making a request."""
    try:
        parsed = urlparse(url)
        port = parsed.port
    except ValueError as exc:
        raise InvalidURL("The URL is malformed.") from exc
    if parsed.scheme.casefold() not in ALLOWED_SCHEMES:
        raise InvalidURL("Only HTTP and HTTPS URLs are allowed.")
    if parsed.username or parsed.password or not parsed.hostname:
        raise InvalidURL("The URL must contain a host and no credentials.")
    if parsed.fragment:
        raise InvalidURL("URL fragments are not supported.")

    port = port or (443 if parsed.scheme.casefold() == "https" else 80)
    try:
        host_address = ipaddress.ip_address(parsed.hostname)
    except (ValueError, UnicodeError):
        await _resolve_public_addresses(parsed.hostname, port)
    else:
        if _is_blocked_address(host_address):
            raise InvalidURL("URLs targeting private or local network addresses are not allowed.")

    return parsed.geturl()


def _content_type(response: httpx.Response) -> str:
    return response.headers.get("content-type", "").split(";", 1)[0].strip().casefold()


async def fetch_text(
    url: str,
    *,
    timeout_seconds: float = 10.0,
    max_bytes: int = 2_000_000,
    max_redirects: int = 3,
) -> FetchedText:
    """Fetch a public text page with bounded redirects, time, and body size."""
    current_url = await validate_url(url)
    timeout = httpx.Timeout(timeout_seconds)

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=False,
            headers={"User-Agent": "FakeRecruiterVerifier/1.0"},
        ) as client:
            for redirect_count in range(max_redirects + 1):
                # Revalidate every hop to prevent redirects into private networks.
                current_url = await validate_url(current_url)
                async with client.stream("GET", current_url) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("location")
                        if not location:
                            raise URLFetchUpstreamError("The upstream redirect had no destination.")
                        if redirect_count >= max_redirects:
                            raise URLFetchUpstreamError("The URL exceeded the redirect limit.")
                        current_url = urljoin(current_url, location)
                        continue

                    if response.status_code >= 400:
                        raise URLFetchUpstreamError(f"The upstream server returned HTTP {response.status_code}.")

                    content_type = _content_type(response)
                    if content_type not in ALLOWED_CONTENT_TYPES:
                        raise URLFetchUnsupportedContent("The URL must return HTML or plain text content.")
                    content_length = response.headers.get("content-length")
                    if content_length:
                        try:
                            if int(content_length) > max_bytes:
                                raise URLFetchTooLarge("The response exceeds the maximum size.")
                        except ValueError as exc:
                            raise URLFetchUpstreamError("The upstream content length was invalid.") from exc

                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > max_bytes:
                            raise URLFetchTooLarge("The response exceeds the maximum size.")
                    encoding = response.encoding or "utf-8"
                    return FetchedText(
                        text=bytes(body).decode(encoding, errors="replace"),
                        final_url=current_url,
                        content_type=content_type,
                    )
    except URLFetchError:
        raise
    except httpx.TimeoutException as exc:
        raise URLFetchTimeout("The upstream server timed out.") from exc
    except httpx.HTTPError as exc:
        raise URLFetchUpstreamError("The upstream request failed.") from exc

    raise URLFetchUpstreamError("The URL could not be fetched.")
