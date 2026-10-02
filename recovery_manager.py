from __future__ import annotations

from collections.abc import Callable, Mapping

from recovery_models import (
    RecoveryAction,
    RecoveryRequest,
    RecoveryResult,
)

RecoveryActionHandler = Callable[
    [RecoveryRequest],
    RecoveryResult,
]


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
        self._action_handlers: dict[
            RecoveryAction,
            RecoveryActionHandler,
        ] = handlers

    @property
    def registered_actions(self) -> tuple[RecoveryAction, ...]:
        return tuple(self._action_handlers.keys())

    def has_handler(self, action: RecoveryAction) -> bool:
        return action in self._action_handlers

    def execute(self, request: RecoveryRequest) -> RecoveryResult:
        if not isinstance(request, RecoveryRequest):
            raise TypeError(
                "request must be RecoveryRequest"
            )
        action = request.recovery_policy.action
        handler = self._action_handlers.get(action)
        if handler is None:
            raise KeyError(
                f"no handler registered for action {action.value}"
            )
        result = handler(request)
        if not isinstance(result, RecoveryResult):
            raise TypeError(
                "handler must return RecoveryResult"
            )
        return result
