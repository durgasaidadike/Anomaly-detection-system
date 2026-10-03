from __future__ import annotations

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
    Validates the structural API contract of incoming payloads.

    The validator intentionally does not contain behavioral intelligence
    or domain-specific event interpretation.

    Optional required_fields allow a later authoritative API contract
    to define required fields without embedding undocumented assumptions
    into Module 15.
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
        """
        Return the configured required fields.
        """

        return self._required_fields

    def validate(
        self,
        payload: Any,
    ) -> ValidationResult:
        """
        Validate the structural payload contract.
        """

        if not isinstance(payload, Mapping):
            return ValidationResult(
                valid=False,
                error="Payload must be a JSON object.",
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