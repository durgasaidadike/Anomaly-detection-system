from __future__ import annotations

from pathlib import Path
from threading import RLock
from uuid import uuid4

from backup_failure import (
    BackupCreationError,
    BackupFailureContext,
    BackupFailureLogger,
    BackupRetryPolicy,
    RecoveryManagerNotifier,
)
from backup_security import (
    BackupSecurityContext,
    BackupSecurityOperation,
)
from backup_integrity import (
    INTEGRITY_ALGORITHM,
    calculate_file_digest,
)
from backup_lifecycle import (
    BackupRetentionEvaluator,
)
from backup_models import (
    BackupMetadata,
    BackupRecord,
)
from backup_storage_port import BackupStoragePort
from recovery_cache import RecoveryCache
from recovery_models import (
    BackupReference,
    FileMetadata,
    RecoveryPolicy,
)


class BackupManager:
    """Coordinates backup creation and maintains
    Backup Manager state.

    Module 14 owns:
    - Backup References
    - Backup Metadata
    - Recovery Cache

    Physical storage is delegated to BackupStoragePort.
    Whether a backup is required is decided upstream by the
    backup requirement boundary; the Backup Manager does not
    evaluate risk, anomaly status, or recovery policy itself.

    Failed backup attempts are logged through an injected
    failure logger and retried according to an injected
    retry policy; a terminal failure is notified to the
    Recovery Manager layer and raised as BackupCreationError
    so an invalid reference is never returned or registered.

    CREATE, VERIFY, and RESTORE are authorized through the
    injected security context before any storage access, so
    an unauthorized operation can never reach the storage
    layer.
    """

    def __init__(
        self,
        storage: BackupStoragePort,
        retention_evaluator: BackupRetentionEvaluator,
        retry_policy: BackupRetryPolicy,
        failure_logger: BackupFailureLogger,
        recovery_manager_notifier: RecoveryManagerNotifier,
        security_context: BackupSecurityContext,
    ) -> None:
        if not isinstance(
            storage,
            BackupStoragePort,
        ):
            raise TypeError(
                "storage must implement BackupStoragePort"
            )
        if not isinstance(
            retention_evaluator,
            BackupRetentionEvaluator,
        ):
            raise TypeError(
                "retention_evaluator must implement "
                "BackupRetentionEvaluator"
            )
        if not isinstance(
            retry_policy,
            BackupRetryPolicy,
        ):
            raise TypeError(
                "retry_policy must implement "
                "BackupRetryPolicy"
            )
        if not isinstance(
            failure_logger,
            BackupFailureLogger,
        ):
            raise TypeError(
                "failure_logger must implement "
                "BackupFailureLogger"
            )
        if not isinstance(
            recovery_manager_notifier,
            RecoveryManagerNotifier,
        ):
            raise TypeError(
                "recovery_manager_notifier must implement "
                "RecoveryManagerNotifier"
            )
        if not isinstance(
            security_context,
            BackupSecurityContext,
        ):
            raise TypeError(
                "security_context must be BackupSecurityContext"
            )
        self._storage = storage
        self._retention_evaluator = retention_evaluator
        self._retry_policy = retry_policy
        self._failure_logger = failure_logger
        self._recovery_manager_notifier = (
            recovery_manager_notifier
        )
        self._security_context = security_context
        self._backup_records: dict[
            str,
            BackupRecord,
        ] = {}
        self._recovery_cache = RecoveryCache()
        self._state_lock = RLock()
        self._source_locks: dict[
            str,
            RLock,
        ] = {}

    def _get_source_lock(
        self,
        file_path: str,
    ) -> RLock:
        """
        Return the lock associated with one source path.
        Different source files receive independent locks so
        unrelated backup requests can proceed independently.
        """
        normalized_path = str(
            Path(file_path).resolve()
        )
        with self._state_lock:
            lock = self._source_locks.get(
                normalized_path
            )
            if lock is None:
                lock = RLock()
                self._source_locks[
                    normalized_path
                ] = lock
            return lock

    @property
    def backup_references(
        self,
    ) -> tuple[BackupReference, ...]:
        return tuple(
            record.reference
            for record in self._backup_records.values()
        )

    @property
    def backup_count(self) -> int:
        return len(self._backup_records)

    @property
    def recovery_cache_size(self) -> int:
        return self._recovery_cache.size

    def get_record(
        self,
        backup_id: str,
    ) -> BackupRecord | None:
        return self._backup_records.get(backup_id)

    def get_backup_record(
        self,
        backup_reference: BackupReference,
    ) -> BackupRecord:
        """
        Return the backup record associated with a valid
        BackupReference.

        The BackupReference remains the lookup boundary;
        callers do not manipulate internal manager state.
        """
        if not isinstance(
            backup_reference,
            BackupReference,
        ):
            raise TypeError(
                "backup_reference must be BackupReference"
            )
        record = self._backup_records.get(
            backup_reference.backup_id
        )
        if record is None:
            raise KeyError(
                f"backup reference not found: "
                f"{backup_reference.backup_id}"
            )
        if record.reference != backup_reference:
            raise KeyError(
                f"backup reference mismatch: "
                f"{backup_reference.backup_id}"
            )
        return record

    def get_backup_metadata(
        self,
        backup_reference: BackupReference,
    ) -> BackupMetadata:
        return self.get_backup_record(
            backup_reference
        ).metadata

    def get_backup_status(
        self,
        backup_reference: BackupReference,
    ) -> str:
        return self.get_backup_record(
            backup_reference
        ).status

    def get_cached_backup_reference(
        self,
        file_metadata: FileMetadata,
    ) -> BackupReference | None:
        """
        Return the cached backup reference for a file,
        when one is available.

        The cache is only an acceleration layer. It does
        not replace BackupManager's authoritative backup
        records.
        """
        if not isinstance(
            file_metadata,
            FileMetadata,
        ):
            raise TypeError(
                "file_metadata must be FileMetadata"
            )
        normalized_path = str(
            Path(
                file_metadata.file_path
            ).resolve()
        )
        reference = self._recovery_cache.get(
            normalized_path
        )
        if reference is None:
            return None
        # Defensive stale-reference check: a cache entry
        # must never outlive the record that authorizes
        # it.
        try:
            record = self.get_backup_record(
                reference
            )
        except KeyError:
            self._recovery_cache.remove(
                normalized_path
            )
            return None
        return record.reference

    def verify_backup(
        self,
        backup_reference: BackupReference,
    ) -> bool:
        """
        Verify that the referenced backup still exists and that
        its contents match the integrity information captured
        when the backup was created.

        Returns False for an unavailable or corrupted backup.
        """
        if not isinstance(
            backup_reference,
            BackupReference,
        ):
            raise TypeError(
                "backup_reference must be BackupReference"
            )
        try:
            record = self.get_backup_record(
                backup_reference
            )
        except KeyError:
            return False

        self._security_context.access_controller.authorize(
            BackupSecurityOperation.VERIFY,
            record.file_metadata,
            backup_reference,
        )

        metadata = record.metadata.values
        algorithm = metadata.get(
            "integrity_algorithm"
        )
        expected_digest = metadata.get(
            "integrity_digest"
        )
        if algorithm != INTEGRITY_ALGORITHM:
            return False
        if (
            not isinstance(expected_digest, str)
            or not expected_digest
        ):
            return False

        backup_path = Path(
            backup_reference.backup_path
        )
        if not backup_path.is_file():
            return False

        try:
            actual_digest = calculate_file_digest(
                backup_path
            )
        except (OSError, ValueError):
            return False
        return actual_digest == expected_digest

    def restore_backup(
        self,
        backup_reference: BackupReference,
        file_metadata: FileMetadata,
    ) -> bool:
        """
        Restore a previously created backup to the file path
        represented by file_metadata.

        Integrity is checked before any restore operation is
        attempted: a corrupted or unavailable backup must never
        be used as a recovery source, so the target is left
        untouched whenever verification fails.

        Returns True only when the backup was verified and the
        storage layer completed the restore.
        """
        if not isinstance(
            backup_reference, BackupReference,
        ):
            raise TypeError(
                "backup_reference must be BackupReference"
            )
        if not isinstance(file_metadata, FileMetadata):
            raise TypeError(
                "file_metadata must be FileMetadata"
            )

        try:
            record = self.get_backup_record(
                backup_reference
            )
        except KeyError:
            return False

        # Authorization precedes integrity verification and
        # the physical restore: a denied request never
        # touches the target file.
        self._security_context.access_controller.authorize(
            BackupSecurityOperation.RESTORE,
            record.file_metadata,
            backup_reference,
        )

        # Verification happens first: the sequence is
        # backup -> verify integrity -> restore, so a
        # corrupted backup never reaches the target.
        if not self.verify_backup(backup_reference):
            return False

        # Storage failures are reported, not raised:
        # the caller asked whether the restore succeeded.
        try:
            self._storage.restore(
                backup_reference,
                Path(file_metadata.file_path),
            )
        except OSError:
            return False
        return True

    def cleanup_backups(self) -> None:
        """
        Remove backups identified as expired by the injected
        retention evaluator.

        Internal records are removed only after the
        corresponding storage entry has been successfully
        deleted. An already-missing storage entry is treated
        as already cleaned and its stale internal record is
        removed.
        """
        candidates = tuple(
            self._backup_records.values()
        )
        for record in candidates:
            try:
                expired = (
                    self._retention_evaluator.is_expired(
                        record
                    )
                )
            except Exception:
                # Retention evaluation failure must not
                # cause an unrelated backup to be deleted.
                continue
            if not expired:
                continue
            try:
                self._storage.delete(record.reference)
            except FileNotFoundError:
                # Storage is already missing; retain no
                # invalid reference, so the stale internal
                # record is removed below.
                pass
            except Exception:
                # Physical deletion failed while the backup
                # still exists, so the record must survive:
                # the manager never claims a backup is gone
                # while its file is still present.
                continue
            # Storage deletion succeeded first, so the
            # manager can never say "backup is gone" while
            # the physical copy still exists. An already-
            # missing backup falls through the same way.
            self._backup_records.pop(
                record.reference.backup_id,
                None,
            )
            source_path = record.metadata.values.get(
                "source_path"
            )
            if (
                isinstance(source_path, str)
                and source_path.strip()
            ):
                normalized_path = str(
                    Path(source_path).resolve()
                )
                self._recovery_cache.remove(
                    normalized_path
                )

    def create_backup(
        self,
        file_metadata: FileMetadata,
        recovery_policy: RecoveryPolicy,
    ) -> BackupReference:
        """
        Create a backup, retrying transient failures according
        to the injected retry policy.

        Every failed attempt is logged. When the policy
        declines to retry (or itself fails), the Recovery
        Manager is notified once and BackupCreationError is
        raised so callers never receive an invalid reference.
        """
        if not isinstance(
            file_metadata,
            FileMetadata,
        ):
            raise TypeError(
                "file_metadata must be FileMetadata"
            )
        if not isinstance(
            recovery_policy,
            RecoveryPolicy,
        ):
            raise TypeError(
                "recovery_policy must be RecoveryPolicy"
            )

        # Access control happens before the source lock and
        # before any storage access: a denied request never
        # becomes a backup attempt.
        self._security_context.access_controller.authorize(
            BackupSecurityOperation.CREATE,
            file_metadata,
        )

        source_lock = self._get_source_lock(
            file_metadata.file_path
        )
        with source_lock:
            return self._create_backup_with_retries(
                file_metadata,
                recovery_policy,
            )

    def _create_backup_with_retries(
        self,
        file_metadata: FileMetadata,
        recovery_policy: RecoveryPolicy,
    ) -> BackupReference:
        """
        Execute backup creation with retry policy enforcement.
        """
        attempt = 1

        while True:
            try:
                return self._create_backup_attempt(
                    file_metadata,
                    recovery_policy,
                )

            except Exception as error:
                context = self._record_backup_failure(
                    file_metadata,
                    attempt,
                    error,
                )

                try:
                    retry = (
                        self._retry_policy.should_retry(
                            attempt,
                            error,
                        )
                    )
                except Exception as retry_error:
                    retry_context = (
                        self._record_backup_failure(
                            file_metadata,
                            attempt,
                            retry_error,
                        )
                    )

                    self._recovery_manager_notifier.notify_failure(
                        retry_context
                    )

                    raise BackupCreationError(
                        retry_context
                    ) from retry_error

                if not retry:
                    self._recovery_manager_notifier.notify_failure(
                        context
                    )

                    raise BackupCreationError(
                        context
                    ) from error

                attempt += 1

    def _record_backup_failure(
        self,
        file_metadata: FileMetadata,
        attempt: int,
        error: BaseException,
    ) -> BackupFailureContext:
        """
        Build and log the context for one failed attempt.

        Logging a failure does not itself alter backup state;
        no reference or record is registered here.
        """
        context = BackupFailureContext(
            operation="CREATE_BACKUP",
            file_metadata=file_metadata,
            attempt=attempt,
            error_type=type(error).__name__,
            error_message=str(error).strip()
            or type(error).__name__,
        )

        self._failure_logger.log_failure(context)

        return context

    def _create_backup_attempt(
        self,
        file_metadata: FileMetadata,
        recovery_policy: RecoveryPolicy,
    ) -> BackupReference:
        """
        Execute exactly one backup attempt.

        Everything before record/cache registration can fail,
        so a failure after the physical copy exists deletes
        the unregistered artifact; retries therefore never
        accumulate orphaned backup files, and a reference is
        never returned before its state is registered.
        """
        source_path = Path(file_metadata.file_path)
        backup_id = f"backup-{uuid4().hex}"
        reference: BackupReference | None = None

        try:
            reference = self._storage.store(
                source_path,
                backup_id,
            )

            if not isinstance(
                reference,
                BackupReference,
            ):
                raise TypeError(
                    "storage must return a BackupReference"
                )

            backup_path = Path(reference.backup_path)

            if (
                not backup_path.exists()
                or not backup_path.is_file()
            ):
                raise RuntimeError(
                    "storage returned an invalid "
                    "backup reference"
                )

            # The integrity digest is captured here, before
            # the record is registered, so a backup that
            # cannot be fingerprinted is never exposed as a
            # valid reference.
            integrity_digest = calculate_file_digest(
                backup_path
            )

            record = BackupRecord(
                reference=reference,
                metadata=self._build_metadata(
                    file_metadata,
                    recovery_policy,
                    reference,
                    integrity_digest,
                ),
                status="CREATED",
                file_metadata=file_metadata,
            )
            self._backup_records[
                reference.backup_id
            ] = record
            normalized_path = str(
                Path(
                    file_metadata.file_path
                ).resolve()
            )
            self._recovery_cache.put(
                normalized_path,
                reference,
            )
            return reference

        except Exception:
            if reference is not None:
                # Roll back any partial registration so a
                # failed attempt never leaves a registered
                # reference to a deleted backup behind.
                self._backup_records.pop(
                    reference.backup_id,
                    None,
                )
                normalized_path = str(
                    Path(
                        file_metadata.file_path
                    ).resolve()
                )
                self._recovery_cache.remove(
                    normalized_path,
                )
                try:
                    self._storage.delete(reference)
                except Exception:
                    # Cleanup failure must not hide the
                    # original backup-creation failure.
                    pass

            raise

    @staticmethod
    def _build_metadata(
        file_metadata: FileMetadata,
        recovery_policy: RecoveryPolicy,
        reference: BackupReference,
        integrity_digest: str,
    ) -> BackupMetadata:
        return BackupMetadata(
            values={
                "source_path": file_metadata.file_path,
                "backup_path": reference.backup_path,
                "file_size": file_metadata.file_size,
                "policy_id": recovery_policy.policy_id,
                "recovery_action": (
                    recovery_policy.action.value
                ),
                "integrity_algorithm": (
                    INTEGRITY_ALGORITHM
                ),
                "integrity_digest": integrity_digest,
            }
        )
