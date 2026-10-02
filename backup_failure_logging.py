from __future__ import annotations

import logging

from backup_failure import BackupFailureContext


class LoggingBackupFailureLogger:
    """
    Adapts the standard Python logging system to the
    BackupFailureLogger protocol.

    No logging format is part of the Module 14 architecture;
    this is only an adapter so production compositions can
    route backup failures through normal application logs.
    """

    def __init__(
        self,
        logger: logging.Logger,
    ) -> None:
        if not isinstance(
            logger,
            logging.Logger,
        ):
            raise TypeError(
                "logger must be logging.Logger"
            )

        self._logger = logger

    def log_failure(
        self,
        context: BackupFailureContext,
    ) -> None:
        self._logger.error(
            "Backup failure: operation=%s "
            "file=%s attempt=%d error_type=%s "
            "message=%s",
            context.operation,
            context.file_metadata.file_path,
            context.attempt,
            context.error_type,
            context.error_message,
        )
