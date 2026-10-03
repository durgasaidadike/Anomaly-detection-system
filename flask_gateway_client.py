from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Optional
from urllib.parse import urlparse

import requests

from flask_gateway_event_adapter import (
    RawEventPayloadAdapter,
)
from watcher import RawEvent


class GatewayTransportError(RuntimeError):
    """
    Raised when communication with the Flask Gateway fails.

    Internal transport details are kept out of the public
    exception message.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        response_payload: Any = None,
    ) -> None:
        super().__init__(message)

        self.status_code = status_code
        self.response_payload = response_payload


class FlaskGatewayClient:
    """
    Outbound communication adapter for the Flask Gateway.

    Responsibilities:
    - Serialize RawEvent objects.
    - Send HTTP requests to the Flask Gateway.
    - Apply an optional request timeout.
    - Interpret HTTP/JSON responses.
    - Convert transport failures into a stable exception.

    This class does not perform behavioral processing.
    """

    def __init__(
        self,
        base_url: str,
        http_client: Optional[Any] = None,
        timeout: Optional[float] = None,
    ) -> None:
        if not isinstance(base_url, str):
            raise TypeError(
                "base_url must be a string."
            )

        base_url = base_url.strip().rstrip("/")

        parsed = urlparse(base_url)

        if parsed.scheme not in {"http", "https"}:
            raise ValueError(
                "base_url must use HTTP or HTTPS."
            )

        if not parsed.netloc:
            raise ValueError(
                "base_url must contain a valid host."
            )

        if timeout is not None:
            if not isinstance(timeout, (int, float)):
                raise TypeError(
                    "timeout must be numeric or None."
                )

            if timeout <= 0:
                raise ValueError(
                    "timeout must be greater than zero."
                )

        self._base_url = base_url
        self._endpoint = (
            f"{base_url}/analyze-event"
        )
        self._timeout = timeout

        self._owns_http_client = (
            http_client is None
        )

        self._http_client = (
            http_client
            if http_client is not None
            else requests.Session()
        )

        if not callable(
            getattr(
                self._http_client,
                "post",
                None,
            )
        ):
            raise TypeError(
                "http_client must provide a callable post method."
            )

    @property
    def endpoint(self) -> str:
        """
        Return the configured analyze-event endpoint.
        """

        return self._endpoint

    def send_event(
        self,
        event: RawEvent,
    ) -> Any:
        """
        Serialize and send one RawEvent to the Flask Gateway.
        """

        payload = RawEventPayloadAdapter.to_payload(
            event
        )

        request_kwargs = {
            "json": payload,
        }

        if self._timeout is not None:
            request_kwargs["timeout"] = self._timeout

        try:
            response = self._http_client.post(
                self._endpoint,
                **request_kwargs,
            )

        except requests.exceptions.Timeout as exc:
            raise GatewayTransportError(
                "Gateway request timed out."
            ) from exc

        except requests.exceptions.RequestException as exc:
            raise GatewayTransportError(
                "Gateway request failed."
            ) from exc

        except Exception as exc:
            raise GatewayTransportError(
                "Gateway transport failed."
            ) from exc

        if not (
            200 <= response.status_code < 300
        ):
            response_payload = self._safe_json(
                response
            )

            raise GatewayTransportError(
                "Gateway returned an unsuccessful HTTP response.",
                status_code=response.status_code,
                response_payload=response_payload,
            )

        try:
            return response.json()

        except (ValueError, TypeError) as exc:
            raise GatewayTransportError(
                "Gateway returned an invalid JSON response.",
                status_code=response.status_code,
            ) from exc

    @staticmethod
    def _safe_json(
        response: Any,
    ) -> Any:
        try:
            return response.json()
        except (ValueError, TypeError):
            return None

    def close(self) -> None:
        """
        Close the internally owned HTTP client.

        Injected clients remain owned by the caller.
        """

        if not self._owns_http_client:
            return

        close = getattr(
            self._http_client,
            "close",
            None,
        )

        if callable(close):
            close()