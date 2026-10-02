from __future__ import annotations

from collections.abc import Callable

from recovery_models import RecoveryRequest, RecoveryResult

RecoveryVerifier = Callable[
    [RecoveryRequest, RecoveryResult],
    bool,
]


class RecoveryVerificationError(RuntimeError):
    """Raised when a recovery result fails verification."""


def verify_recovery(
    request: RecoveryRequest,
    result: RecoveryResult,
    verifier: RecoveryVerifier,
) -> RecoveryResult:
    """
    Verify the outcome of an executed recovery action.

    Filesystem-specific verification remains outside this
    helper and is supplied through the injected verifier.
    """
    if not isinstance(
        request,
        RecoveryRequest,
    ):
        raise TypeError(
            "request must be RecoveryRequest"
        )
    if not isinstance(
        result,
        RecoveryResult,
    ):
        raise TypeError(
            "result must be RecoveryResult"
        )
    if not callable(verifier):
        raise TypeError(
            "verifier must be callable"
        )
    verified = verifier(request, result)
    if not isinstance(verified, bool):
        raise TypeError(
            "verifier must return bool"
        )
    if not verified:
        raise RecoveryVerificationError(
            "recovery result failed verification"
        )
    return result
