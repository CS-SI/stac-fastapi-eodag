"""Midlewares for the eodag FastAPI application."""

import contextlib
from typing import Any, Tuple

from stac_fastapi.api.middleware import _HOST_HEADER_REGEX, _PROTO_HEADER_REGEX
from stac_fastapi.api.middleware import ProxyHeaderMiddleware as BaseProxyHeaderMiddleware
from starlette.types import Scope


class ProxyHeaderMiddleware(BaseProxyHeaderMiddleware):
    """
    Override the one from STAC FastAPI to properly handle port from Forwarded header.
    """

    def _get_forwarded_url_parts(self, scope: Scope) -> Tuple[Any, Any, Any]:
        proto = scope.get("scheme", "http")
        header_host = self._get_header_value_by_name(scope, "host")
        if header_host is None:
            domain, port = scope.get("server", ("", ""))
        else:
            header_host_parts = header_host.split(":")
            if len(header_host_parts) == 2:
                domain, port = header_host_parts
            else:
                domain = header_host_parts[0]
                port = None

        port_str = None  # make sure it is defined in all paths since we access it later

        if forwarded := self._get_header_value_by_name(scope, "forwarded"):
            for proxy in forwarded.split(","):
                if proto_expr := _PROTO_HEADER_REGEX.search(proxy):
                    proto = proto_expr.group("proto")
                if host_expr := _HOST_HEADER_REGEX.search(proxy):
                    domain = host_expr.group("host")
                    port_str = host_expr.group("port")
            if port_str is None:
                port_str = "443" if proto == "https" else "80"

        else:
            domain = self._get_header_value_by_name(scope, "x-forwarded-host", domain)
            proto = self._get_header_value_by_name(scope, "x-forwarded-proto", proto)
            port_str = self._get_header_value_by_name(scope, "x-forwarded-port", port)

        with contextlib.suppress(ValueError):  # ignore ports that are not valid integers
            port = int(port_str) if port_str is not None else port

        return (proto, domain, port)
