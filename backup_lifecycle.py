from __future__ import annotations

from typing import Protocol, runtime_checkable

from backup_models import BackupRecord


@runtime_checkable
class BackupRetentionEvaluator(Protocol):
    """
    Determines whether a backup record is expired.

    The retention/expiration rule is intentionally injected
    because Module 14 does not prescribe a fixed duration,
    timestamp rule, or expiry formula.
    """

    def is_expired(
        self,
        record: BackupRecord,
    ) -> bool:
        ...