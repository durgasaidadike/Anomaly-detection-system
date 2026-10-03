from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """
    Result of Gateway request validation.
    """

    valid: bool
    error: Optional[str] = None
    missing_fields: tuple[str, ...] = ()


class GatewayPayloadValidator:
    """
    Validates and sanitizes the structural API payload.

    This validator does not interpret filesystem behavior,
    calculate features, perform anomaly detection, or make decisions.
    """

    def __init__(
        self,
        required_fields: tuple[str, ...] = (),
    ) -> None:
        normalized_fields = []

        for field in required_fields:
            if not isinstance(field, str):
                raise TypeError(
                    "required_fields must contain only strings."
                )

            field = field.strip()

            if not field:
                raise ValueError(
                    "required_fields cannot contain empty names."
                )

            normalized_fields.append(field)

        if len(set(normalized_fields)) != len(normalized_fields):
            raise ValueError(
                "required_fields cannot contain duplicates."
            )

        self._required_fields = tuple(normalized_fields)

    @property
    def required_fields(self) -> tuple[str, ...]:
        return self._required_fields

    def validate(
        self,
        payload: Any,
    ) -> ValidationResult:
        if not isinstance(payload, Mapping):
            return ValidationResult(
                valid=False,
                error="Payload must be a JSON object.",
            )

        try:
            self._sanitize_value(payload)

        except (TypeError, ValueError) as exc:
            return ValidationResult(
                valid=False,
                error=str(exc),
            )

        missing_fields = tuple(
            field
            for field in self._required_fields
            if field not in payload
        )

        if missing_fields:
            return ValidationResult(
                valid=False,
                error="Missing required fields.",
                missing_fields=missing_fields,
            )

        return ValidationResult(valid=True)

    def sanitize(
        self,
        payload: Any,
    ) -> dict[str, Any]:
        """
        Return a fresh JSON-safe copy of the payload.

        The returned structure is detached from the Flask request
        object so downstream processing cannot mutate the original
        request-owned structure.
        """

        if not isinstance(payload, Mapping):
            raise TypeError(
                "Payload must be a JSON object."
            )

        sanitized = self._sanitize_value(payload)

        if not isinstance(sanitized, dict):
            raise TypeError(
                "Sanitized payload must be a JSON object."
            )

        return sanitized

    def _sanitize_value(
        self,
        value: Any,
    ) -> Any:
        if value is None:
            return None

        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            return value

        if isinstance(value, int):
            return value

        if isinstance(value, float):
            if not math.isfinite(value):
                raise ValueError(
                    "Payload contains a non-finite numeric value."
                )

            return value

        if isinstance(value, Mapping):
            sanitized_mapping: dict[str, Any] = {}

            for key, nested_value in value.items():
                if not isinstance(key, str):
                    raise TypeError(
                        "JSON object keys must be strings."
                    )

                sanitized_mapping[key] = (
                    self._sanitize_value(nested_value)
                )

            return sanitized_mapping

        if isinstance(value, list):
            return [
                self._sanitize_value(item)
                for item in value
            ]

        raise TypeError(
            "Payload contains an unsupported value type."
        )