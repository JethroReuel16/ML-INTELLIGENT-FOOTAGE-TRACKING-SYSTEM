"""
Rules for what a video source may point at.

Every place that opens a source (registration, edits, connection tests and
searches) goes through these checks, so the rules cannot drift apart.

- File sources ("local" / "network") may only read inside ALLOWED_SOURCE_ROOTS.
  In production they are disabled entirely until roots are configured, so a
  user can never make the server read arbitrary files.
- Network sources ("http" / "rtsp") may never target link-local / cloud
  metadata addresses (classic SSRF targets). Loopback is refused in
  production. Private LAN addresses stay allowed: CCTV cameras live there.
"""

import ipaddress
import os
import socket
from urllib.parse import urlsplit

from fastapi import HTTPException

from app.config import settings

# Cloud metadata endpoints that are not covered by the link-local range.
_METADATA_ADDRESSES = {
    ipaddress.ip_address("fd00:ec2::254"),  # AWS IPv6 metadata
}


def _forbidden(detail: str) -> HTTPException:
    return HTTPException(status_code=403, detail=detail)


def file_sources_enabled() -> bool:
    return bool(settings.allowed_source_roots) or not settings.is_production


def check_file_source(path: str) -> None:
    """Raise 403 unless a local/network path may be read by the server."""

    if not file_sources_enabled():
        raise _forbidden(
            "Local and network file sources are disabled on this server. "
            "An administrator must set ALLOWED_SOURCE_ROOTS to enable them."
        )

    if not settings.allowed_source_roots:
        return  # development without an allow-list

    real = os.path.realpath(os.path.abspath(path))

    for root in settings.allowed_source_roots:
        root_real = os.path.realpath(root)
        try:
            if os.path.commonpath([real, root_real]) == root_real:
                return
        except ValueError:  # different drive on Windows
            continue

    raise _forbidden("This path is outside the folders the server is allowed to read.")


def _address_problem(address) -> str | None:
    if address in _METADATA_ADDRESSES:
        return "a cloud metadata address"
    if address.is_link_local:
        return "a link-local address"
    if address.is_unspecified or address.is_multicast or address.is_reserved:
        return "a reserved address"
    if address.is_loopback and not settings.allow_loopback_sources:
        return "this server itself (loopback)"
    return None


def check_network_target(url: str) -> None:
    """Raise 403 if an http(s)/rtsp(s) URL points somewhere it must not."""

    try:
        host = urlsplit(url).hostname
    except ValueError as error:
        raise HTTPException(status_code=400, detail="The source URL is not valid.") from error

    if not host:
        raise HTTPException(status_code=400, detail="The source URL has no host name.")

    try:
        literal = ipaddress.ip_address(host)
        addresses = [literal]
    except ValueError:
        try:
            infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
        except (socket.gaierror, UnicodeError):
            # Unresolvable now (camera offline / DNS later): the connection
            # will simply fail; nothing is reachable through it.
            return
        addresses = []
        for info in infos:
            try:
                addresses.append(ipaddress.ip_address(info[4][0].split("%")[0]))
            except ValueError:
                continue

    for address in addresses:
        problem = _address_problem(address)
        if problem:
            raise _forbidden(f"Video sources may not point at {problem}.")


def check_source(source_type: str, url: str) -> None:
    """Apply the right policy for a registered source."""
    source_type = (source_type or "").strip().lower()

    if source_type in {"local", "network"}:
        check_file_source(url)
    elif source_type in {"http", "rtsp"}:
        check_network_target(url)
