from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from typing import Any, Optional, Protocol

from flask import Flask, Request, jsonify, request


logger = logging.getLogger(__name__)


class EventProcessor(Protocol):
    """
    Boundary for the Python behavioral intelligence pipeline.

    The Flask Gateway knows only that it receives a JSON-compatible
    mapping and returns a response-compatible result.

    Business logic remains outside the Gateway.
    """

    def __call__(
        self,
        payload: Mapping[str, Any],
    ) -> Any:
        ...


class RequestAuthorizer(Protocol):
    """
    Optional authorization boundary.

    Authentication/authorization mechanics are intentionally injected
    rather than implemented inside the Flask Gateway because the
    Module 15 specification does not define a concrete auth protocol.
    """

    def __call__(
        self,
        request: Request,
    ) -> bool:
        ...


class FlaskGateway:
    """
    PRISM Module 15 - Flask Gateway.

    Responsibilities:
    - Receive API requests.
    - Validate request structure.
    - Route requests.
    - Invoke the injected Python pipeline.
    - Return API responses.
    - Log gateway failures.

    This class deliberately contains:
    - No ML logic.
    - No behavioral analysis.
    - No Candidate Pattern logic.
    - No behavioral persistence.
    - No recovery logic.

    The Gateway is stateless with respect to request processing.
    """

    def __init__(
        self,
        event_processor: EventProcessor,
        authorizer: Optional[RequestAuthorizer] = None,
    ) -> None:
        if not callable(event_processor):
            raise TypeError(
                "event_processor must be callable."
            )

        if authorizer is not None and not callable(authorizer):
            raise TypeError(
                "authorizer must be callable when provided."
            )

        self._event_processor = event_processor
        self._authorizer = authorizer

    def create_app(self) -> Flask:
        """
        Create and configure the Flask application.

        A new Flask application can be created for testing or
        deployment without introducing request-specific state.
        """

        app = Flask(__name__)

        app.add_url_rule(
            "/health",
            view_func=self.health,
            methods=["GET"],
        )

        app.add_url_rule(
            "/status",
            view_func=self.status,
            methods=["GET"],
        )

        app.add_url_rule(
            "/analyze-event",
            view_func=self.analyze_event,
            methods=["POST"],
        )

        return app

    def _is_authorized(self) -> bool:
        """
        Evaluate the optional authorization boundary.

        No concrete authentication scheme is assumed here.
        """

        if self._authorizer is None:
            return True

        try:
            return bool(self._authorizer(request))
        except Exception:
            logger.exception(
                "Authorization handler failed."
            )
            return False

    @staticmethod
    def _validate_json_object() -> Optional[Mapping[str, Any]]:
        """
        Validate that the request contains a JSON object.

        Returns the decoded mapping when valid.
        Returns None when the request is invalid.
        """

        if not request.is_json:
            return None

        payload = request.get_json(silent=True)

        if not isinstance(payload, dict):
            return None

        return payload

    def health(self):
        """
        Gateway health endpoint.

        No behavioral processing is performed.
        """

        return jsonify(
            {
                "status": "ok",
            }
        ), 200

    def status(self):
        """
        Gateway status endpoint.

        This reports Gateway availability only; it does not
        calculate behavioral or system intelligence.
        """

        return jsonify(
            {
                "status": "ready",
            }
        ), 200

    def analyze_event(self):
        """
        Receive an event request and forward it to the injected
        Python processing boundary.
        """

        if not self._is_authorized():
            return jsonify(
                {
                    "error": "Request not authorized.",
                }
            ), 403

        payload = self._validate_json_object()

        if payload is None:
            return jsonify(
                {
                    "error": "Request must contain a JSON object.",
                }
            ), 400

        try:
            result = self._event_processor(payload)

        except TimeoutError:
            logger.exception(
                "Behavioral pipeline request timed out."
            )

            return jsonify(
                {
                    "error": "Request processing timed out.",
                }
            ), 504

        except Exception:
            logger.exception(
                "Behavioral pipeline processing failed."
            )

            return jsonify(
                {
                    "error": "Request processing failed.",
                }
            ), 500

        try:
            return jsonify(result), 200

        except TypeError:
            logger.exception(
                "Behavioral pipeline returned a non-JSON-compatible result."
            )

            return jsonify(
                {
                    "error": "Invalid processing response.",
                }
            ), 500


def create_app(
    event_processor: EventProcessor,
    authorizer: Optional[RequestAuthorizer] = None,
) -> Flask:
    """
    Application factory for PRISM Flask Gateway.
    """

    gateway = FlaskGateway(
        event_processor=event_processor,
        authorizer=authorizer,
    )

    return gateway.create_app()