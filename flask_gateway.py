from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any, Optional, Protocol

from flask import Flask, Request, jsonify, request

from flask_gateway_validation import (
    GatewayPayloadValidator,
)


logger = logging.getLogger(__name__)


class EventProcessor(Protocol):
    """
    Boundary for the Python behavioral intelligence pipeline.
    """

    def __call__(
        self,
        payload: Mapping[str, Any],
    ) -> Any:
        ...


class RequestAuthorizer(Protocol):
    """
    Optional authorization boundary.

    A concrete authentication mechanism is intentionally not defined
    here because Module 15 does not specify one.
    """

    def __call__(
        self,
        request: Request,
    ) -> bool:
        ...


class FlaskGateway:
    """
    PRISM Module 15 - Flask Gateway.

    Communication responsibilities only:
    - Receive API requests.
    - Validate requests.
    - Route requests.
    - Invoke the Python pipeline.
    - Return responses.
    - Log gateway failures.

    No behavioral intelligence belongs here.
    """

    def __init__(
        self,
        event_processor: EventProcessor,
        validator: Optional[GatewayPayloadValidator] = None,
        authorizer: Optional[RequestAuthorizer] = None,
        max_content_length: Optional[int] = None,
    ) -> None:
        if not callable(event_processor):
            raise TypeError(
                "event_processor must be callable."
            )

        if validator is not None and not isinstance(
            validator,
            GatewayPayloadValidator,
        ):
            raise TypeError(
                "validator must be a GatewayPayloadValidator."
            )

        if authorizer is not None and not callable(authorizer):
            raise TypeError(
                "authorizer must be callable when provided."
            )

        if max_content_length is not None:
            if not isinstance(max_content_length, int):
                raise TypeError(
                    "max_content_length must be an integer or None."
                )

            if max_content_length <= 0:
                raise ValueError(
                    "max_content_length must be greater than zero."
                )

        self._event_processor = event_processor
        self._validator = (
            validator
            or GatewayPayloadValidator()
        )
        self._authorizer = authorizer
        self._max_content_length = max_content_length

    def create_app(self) -> Flask:
        """
        Create and configure the Flask application.
        """

        app = Flask(__name__)

        if self._max_content_length is not None:
            app.config["MAX_CONTENT_LENGTH"] = (
                self._max_content_length
            )

        app.register_error_handler(
            413,
            self._handle_payload_too_large,
        )

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

    @staticmethod
    def _handle_payload_too_large(_error):
        """
        Handle requests exceeding the configured Gateway payload limit.
        """

        return jsonify(
            {
                "error": "Request payload is too large.",
            }
        ), 413

    def _is_authorized(self) -> bool:
        """
        Evaluate the optional authorization boundary.
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
    def _get_json_payload() -> Any:
        """
        Decode JSON without allowing Flask to raise a parsing exception.
        """

        if not request.is_json:
            return None

        return request.get_json(silent=True)

    def health(self):
        """
        Gateway health endpoint.
        """

        return jsonify(
            {
                "status": "ok",
            }
        ), 200

    def status(self):
        """
        Gateway status endpoint.
        """

        return jsonify(
            {
                "status": "ready",
            }
        ), 200

    def analyze_event(self):
        """
        Receive an event request and forward it to the
        injected Python processing boundary.
        """

        if not self._is_authorized():
            return jsonify(
                {
                    "error": "Request not authorized.",
                }
            ), 403

        payload = self._get_json_payload()

        if payload is None:
            return jsonify(
                {
                    "error": "Request must contain a JSON object.",
                }
            ), 400

        validation = self._validator.validate(payload)

        if not validation.valid:
            response = {
                "error": validation.error,
            }

            if validation.missing_fields:
                response["missing_fields"] = list(
                    validation.missing_fields
                )

            return jsonify(response), 400

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
    validator: Optional[GatewayPayloadValidator] = None,
    authorizer: Optional[RequestAuthorizer] = None,
    max_content_length: Optional[int] = None,
) -> Flask:
    """
    Application factory for the PRISM Flask Gateway.
    """

    gateway = FlaskGateway(
        event_processor=event_processor,
        validator=validator,
        authorizer=authorizer,
        max_content_length=max_content_length,
    )

    return gateway.create_app()