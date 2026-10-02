from __future__ import annotations

import logging

from collections.abc import Callable, Mapping

from recovery_models import (
    RecoveryAction,
    RecoveryRequest,
    RecoveryResult,
)
from recovery_verification import (
    RecoveryVerificationError,
    RecoveryVerifier,
    verify_recovery,
)

RecoveryActionHandler = Callable[
    [RecoveryRequest],
    RecoveryResult,
]

RecoveryFailureHandler = Callable[
    [RecoveryRequest, Exception],
    RecoveryResult,
]

logger = logging.getLogger(__name__)


class RecoveryManager:
    """
    Coordinates approved recovery workflows.

    This class owns orchestration only.
    It does NOT:
    - perform anomaly detection,
    - execute ML inference,
    - mutate stored knowledge,
    - own backup lifecycle,
    - implement filesystem mechanics directly.
    """

    def __init__(
        self,
        action_handlers: Mapping[
            RecoveryAction,
            RecoveryActionHandler,
        ],
        failure_handler: RecoveryFailureHandler,
        verification_handler: RecoveryVerifier,
    ) -> None:
        if not isinstance(action_handlers, Mapping):
            raise TypeError(
                "action_handlers must be a mapping"
            )
        handlers = dict(action_handlers)
        if not handlers:
            raise ValueError(
                "action_handlers must not be empty"
            )
        for action, handler in handlers.items():
            if not isinstance(action, RecoveryAction):
                raise TypeError(
                    "action_handlers keys must be RecoveryAction"
                )
            if not callable(handler):
                raise TypeError(
                    "action_handlers values must be callable"
                )
        if not callable(failure_handler):
            raise TypeError(
                "failure_handler must be callable"
            )
        if not callable(verification_handler):
            raise TypeError(
                "verification_handler must be callable"
            )
        self._action_handlers: dict[
            RecoveryAction,
            RecoveryActionHandler,
        ] = handlers
        self._failure_handler = failure_handler
        self._verification_handler = verification_handler

    @property
    def registered_actions(self) -> tuple[RecoveryAction, ...]:
        return tuple(self._action_handlers.keys())

    def has_handler(self, action: RecoveryAction) -> bool:
        return action in self._action_handlers

    _BACKUP_REQUIRED_ACTIONS = frozenset(
        {
            RecoveryAction.RESTORE_PREVIOUS_VERSION,
            RecoveryAction.ROLLBACK_OPERATION,
        }
    )

    @classmethod
    def _validate_backup_requirement(
        cls,
        request: RecoveryRequest,
    ) -> None:
        action = request.recovery_policy.action
        if (
            action in cls._BACKUP_REQUIRED_ACTIONS
            and request.backup_reference is None
        ):
            raise ValueError(
                f"{action.value} requires "
                "a valid BackupReference"
            )

    def execute(self, request: RecoveryRequest) -> RecoveryResult:
        if not isinstance(request, RecoveryRequest):
            raise TypeError(
                "request must be RecoveryRequest"
            )
        self._validate_backup_requirement(request)
        action = request.recovery_policy.action
        handler = self._action_handlers.get(action)
        if handler is None:
            raise KeyError(
                f"no handler registered for action {action.value}"
            )
        try:
            result = handler(request)
        except Exception as exc:
            logger.exception(
                "Recovery action failed: %s",
                request.recovery_policy.action.value,
            )
            failure_result = self._failure_handler(
                request,
                exc,
            )
            if not isinstance(
                failure_result,
                RecoveryResult,
            ):
                raise TypeError(
                    "failure_handler must return "
                    "RecoveryResult"
                )
            return failure_result
        if not isinstance(result, RecoveryResult):
            raise TypeError(
                "recovery action handler must return "
                "RecoveryResult"
            )
        try:
            return verify_recovery(
                request,
                result,
                self._verification_handler,
            )
        except RecoveryVerificationError as exc:
            logger.exception(
                "Recovery verification failed."
            )
            failure_result = self._failure_handler(
                request,
                exc,
            )
            if not isinstance(
                failure_result,
                RecoveryResult,
            ):
                raise TypeError(
                    "failure_handler must return "
                    "RecoveryResult"
                )
            return failure_result
