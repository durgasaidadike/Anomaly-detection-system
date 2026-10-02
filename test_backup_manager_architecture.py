import ast
from pathlib import Path

from backup_manager_port import BackupManagerPort
from recovery_models import (
    RecoveryAction,
    RecoveryPolicy,
)
from test_recovery_backup_integration import (
    build_file_metadata,
    build_real_manager,
)

ROOT = Path(__file__).resolve().parent

# Central list of Module 14 production files. Adjust only
# when a production file actually belongs to Module 14.
BACKUP_FILES = (
    "backup_manager.py",
    "backup_models.py",
    "backup_manager_port.py",
    "backup_storage_port.py",
    "filesystem_backup_storage.py",
    "backup_integrity.py",
    "backup_requirement.py",
    "backup_lifecycle.py",
    "backup_failure.py",
    "backup_failure_logging.py",
    "backup_security.py",
    "recovery_cache.py",
    "recovery_backup_integration.py",
)

# The only backup-layer file allowed to touch the real
# filesystem. Everything else stays storage-free.
FILESYSTEM_STORAGE_FILE = "filesystem_backup_storage.py"

FILESYSTEM_MUTATION_TOKENS = (
    "shutil",
    "os.replace",
    "os.remove",
    "os.rename",
    "tempfile",
    "path.unlink",
    "path.rename",
    ".mkdir(",
    "copy2",
)

FORBIDDEN_IMPORT_TOKENS = {
    "pymongo",
    "motor",
    "sqlalchemy",
    "sqlite3",
    "flask",
    "sklearn",
    "numpy",
    "torch",
    "shutil",
    "decision_engine",
    "machine_learning_engine",
    "candidate_pattern_manager",
    "similarity_engine",
    "drift_engine",
    "confidence_engine",
    "behavior_analyzer",
}

FORBIDDEN_SOURCE_TOKENS = (
    "pymongo",
    "motor",
    "sqlite3",
    "sqlalchemy",
    "mongodb",
    "insert_one",
    "update_one",
    "find_one",
    "shutil",
    "os.remove",
    "os.rename",
    "os.replace",
    "path.unlink",
    "path.rename",
    "anomaly_score",
    "make_decision",
    "classify_risk",
    "behavioral_history",
    "candidate_pattern",
)

# Chunk 13: Module 14 must not absorb the intelligence
# responsibilities that belong to other modules.
FORBIDDEN_INTELLIGENCE_MODULES = {
    "sklearn",
    "numpy",
    "scipy",
    "machine_learning_engine",
    "ml_inference_engine",
    "behavior_analyzer",
    "candidate_pattern_manager",
    "pattern_repository",
    "similarity_engine",
    "drift_engine",
    "confidence_engine",
}

# Backup state lives here, but Module 14 must not become a
# database subsystem; legitimate filesystem storage stays
# allowed in the storage implementation.
FORBIDDEN_PERSISTENCE_MODULES = {
    "sqlite3",
    "pymongo",
    "sqlalchemy",
    "motor",
}


def read_tree(filename: str) -> ast.Module:
    path = ROOT / filename
    return ast.parse(
        path.read_text(encoding="utf-8"),
        filename=str(path),
    )


def imported_modules(
    tree: ast.Module,
) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(
                    alias.name.split(".")[0].lower()
                )
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.add(
                    node.module.split(".")[0].lower()
                )
    return modules


def test_all_backup_source_files_exist():
    missing = [
        filename
        for filename in BACKUP_FILES
        if not (ROOT / filename).exists()
    ]
    assert not missing, f"Missing backup files: {missing}"


def test_backup_layer_has_no_forbidden_imports():
    violations = []
    for filename in BACKUP_FILES:
        if filename == FILESYSTEM_STORAGE_FILE:
            # The storage implementation is allowed the
            # filesystem primitives the others are denied.
            continue
        imported = imported_modules(read_tree(filename))
        forbidden = {
            module
            for module in imported
            for token in FORBIDDEN_IMPORT_TOKENS
            if token in module
        }
        if forbidden:
            violations.append((filename, sorted(forbidden)))
    assert not violations, violations


def test_backup_layer_has_no_storage_or_ml_tokens():
    violations = []
    for filename in BACKUP_FILES:
        if filename == FILESYSTEM_STORAGE_FILE:
            # Storage is the one file allowed to perform
            # filesystem mechanics.
            continue
        content = (ROOT / filename).read_text(
            encoding="utf-8"
        ).lower()
        found = [
            token
            for token in FORBIDDEN_SOURCE_TOKENS
            if token in content
        ]
        if found:
            violations.append((filename, found))
    assert not violations, violations


def test_filesystem_storage_file_exists():
    assert (
        ROOT / FILESYSTEM_STORAGE_FILE
    ).exists(), (
        "The concrete Backup Storage implementation "
        "is missing."
    )


def test_filesystem_mechanics_are_confined_to_storage():
    """Only filesystem_backup_storage.py may perform
    filesystem mutation. Every other backup-layer file
    stays storage-free."""
    violations = []
    for filename in BACKUP_FILES:
        if filename == FILESYSTEM_STORAGE_FILE:
            # This is the file the rule excepts.
            continue
        content = (ROOT / filename).read_text(
            encoding="utf-8"
        ).lower()
        found = [
            token
            for token in FILESYSTEM_MUTATION_TOKENS
            if token in content
        ]
        if found:
            violations.append((filename, found))
    assert not violations, violations


def test_backup_manager_delegates_storage_through_port():
    """backup_manager.py must reach storage only via the
    injected BackupStoragePort, never via shutil/os."""
    content = (
        ROOT / "backup_manager.py"
    ).read_text(encoding="utf-8")
    assert "BackupStoragePort" in content
    assert "_storage.store(" in content
    assert "_storage.restore(" in content
    assert "_storage.delete(" in content
    for token in FILESYSTEM_MUTATION_TOKENS:
        assert token not in content.lower()


def test_backup_storage_port_declares_restore_and_delete():
    """restore/delete are storage operations: the
    production protocol itself must declare them, not
    the tests."""
    content = (
        ROOT / "backup_storage_port.py"
    ).read_text(encoding="utf-8")
    assert "def restore(" in content
    assert "destination_path" in content
    assert "def delete(" in content


def test_integrity_algorithm_lives_in_metadata_not_as_a_rule():
    """sha256 is the concrete implementation stored in
    metadata; the manager references the algorithm only
    through the integrity module, never inline."""
    manager_content = (
        ROOT / "backup_manager.py"
    ).read_text(encoding="utf-8")
    integrity_content = (
        ROOT / "backup_integrity.py"
    ).read_text(encoding="utf-8")
    assert "sha256" not in manager_content.lower()
    assert "INTEGRITY_ALGORITHM" in manager_content
    assert "sha256" in integrity_content


def test_integrity_module_streams_files():
    """calculate_file_digest must read in chunks so
    potentially large backups are not loaded whole."""
    content = (
        ROOT / "backup_integrity.py"
    ).read_text(encoding="utf-8")
    assert "CHUNK_SIZE" in content
    assert "CHUNK_SIZE" in content.split(
        "def calculate_file_digest"
    )[1]


def test_backup_manager_does_not_define_retention_duration():
    """Module 14's specification provides no retention
    duration, so Backup Manager must not silently invent
    one."""
    source = Path(__file__).parent / "backup_manager.py"
    text = source.read_text(encoding="utf-8").lower()
    forbidden_terms = {
        "7 days",
        "24 hours",
        "retention_days",
        "expiry_days",
        "expiration_days",
        "timedelta(days=",
    }
    for term in forbidden_terms:
        assert term not in text


def test_recovery_cache_stores_only_backup_references():
    """Module 14: the cache holds only what rapid recovery
    needs - never full metadata or records."""
    source = (
        Path(__file__).parent
        / "recovery_cache.py"
    )
    text = source.read_text(
        encoding="utf-8"
    )
    assert "BackupReference" in text
    assert "BackupMetadata" not in text
    assert "BackupRecord" not in text


def test_recovery_cache_has_no_ml_or_behavioral_dependencies():
    """The recovery cache must never drift into becoming an
    intelligence subsystem."""
    tree = read_tree(
        "recovery_cache.py"
    )
    forbidden = {
        "sklearn",
        "numpy",
        "scipy",
        "behavior_analyzer",
        "pattern_repository",
        "candidate_pattern_manager",
        "decision_engine",
    }
    assert imported_modules(tree).isdisjoint(forbidden)


def test_backup_manager_does_not_define_retry_count():
    """Module 14 does not prescribe a retry count, so the
    orchestrator must never hardcode one either; retry
    configuration stays in the injected policy."""
    source = (
        Path(__file__).parent
        / "backup_manager.py"
    )
    text = source.read_text(
        encoding="utf-8"
    ).lower()

    forbidden = {
        "max_attempts=3",
        "max_attempts=5",
        "retry_count = 3",
        "retry_count = 5",
    }

    for term in forbidden:
        assert term not in text


def test_backup_manager_uses_failure_boundaries():
    """Failure logging, retry decisions, and Recovery Manager
    notification all flow through injected backup_failure
    boundaries rather than ad-hoc mechanisms."""
    tree = read_tree(
        "backup_manager.py"
    )

    imported = imported_modules(tree)

    assert "backup_failure" in imported


def test_backup_manager_uses_per_source_concurrency_control():
    source = (
        Path(__file__).parent
        / "backup_manager.py"
    )
    text = source.read_text(
        encoding="utf-8"
    )
    assert "RLock" in text
    assert "_source_locks" in text


def test_backup_manager_does_not_use_asyncio_for_backup_lifecycle():
    source = (
        Path(__file__).parent
        / "backup_manager.py"
    )
    text = source.read_text(
        encoding="utf-8"
    )
    assert "asyncio" not in text


def test_filesystem_backup_storage_does_not_directly_unlink_backups():
    """Chunk 12: backup removal flows through the injected
    secure-deletion provider; no direct unlink of backup
    files survives in the storage implementation."""
    source = (
        Path(__file__).parent
        / "filesystem_backup_storage.py"
    )
    text = source.read_text(encoding="utf-8")
    assert ".unlink()" not in text
    assert (
        "_secure_deletion_provider.secure_delete("
        in text
    )


def test_backup_manager_does_not_embed_crypto_algorithm():
    """Chunks 12/13: encryption stays behind the provider
    boundary; Backup Manager never embeds an algorithm or
    key-management scheme the specification does not define."""
    source = (
        Path(__file__).parent
        / "backup_manager.py"
    )
    text = source.read_text(
        encoding="utf-8"
    ).lower()
    forbidden = {
        "aesgcm(",
        "fernet(",
        "cryptography.fernet",
        "cryptography.hazmat",
        "private_key",
        "secret_key",
    }
    for token in forbidden:
        assert token not in text


def test_backup_manager_authorizes_operations_through_security_boundary():
    """Chunk 12: CREATE, VERIFY, and RESTORE each pass through
    the injected access controller exactly once, before any
    storage access."""
    source = (
        Path(__file__).parent
        / "backup_manager.py"
    )
    text = source.read_text(encoding="utf-8")
    tree = ast.parse(text)
    assert "backup_security" in imported_modules(tree)
    assert text.count(".authorize(") == 3
    for operation in (
        "BackupSecurityOperation.CREATE",
        "BackupSecurityOperation.VERIFY",
        "BackupSecurityOperation.RESTORE",
    ):
        assert operation in text


def test_all_backup_production_files_parse():
    """Chunk 13: every Module 14 production file must at
    least parse - catches accidental truncation."""
    for filename in BACKUP_FILES:
        path = ROOT / filename

        assert path.exists(), (
            f"Missing Module 14 production file: "
            f"{filename}"
        )

        ast.parse(
            path.read_text(
                encoding="utf-8"
            ),
            filename=str(path),
        )


def test_backup_production_files_have_no_intelligence_dependencies():
    """Chunk 13: no anomaly detection, ML, behavioral-history,
    or pattern-generation responsibility may leak into
    Module 14."""
    for filename in BACKUP_FILES:
        tree = read_tree(filename)

        imported = imported_modules(tree)

        assert imported.isdisjoint(
            FORBIDDEN_INTELLIGENCE_MODULES
        ), filename


def test_backup_manager_does_not_directly_use_database_clients():
    """Chunk 13: backup state belongs to Backup Manager, but
    the module must not become a database subsystem."""
    tree = read_tree(
        "backup_manager.py"
    )

    assert imported_modules(tree).isdisjoint(
        FORBIDDEN_PERSISTENCE_MODULES
    )


def test_backup_manager_does_not_import_filesystem_copy_primitives():
    """Chunk 13: Backup Manager orchestrates; physical
    filesystem mechanics belong to Backup Storage. pathlib
    stays allowed for metadata/path handling."""
    tree = read_tree(
        "backup_manager.py"
    )

    imported = imported_modules(tree)

    forbidden = {
        "shutil",
        "os",
        "tempfile",
    }

    assert imported.isdisjoint(forbidden)


def test_filesystem_storage_contains_physical_copy_logic():
    """Chunk 13: the actual copy mechanism must live in
    Backup Storage, nowhere else."""
    tree = read_tree(
        "filesystem_backup_storage.py"
    )

    assert "shutil" in imported_modules(tree)


def test_backup_manager_port_contains_only_sealed_operations():
    """Chunk 13: the Module 13 contract stays sealed to
    create/restore/verify - nothing else may creep in."""
    source = (
        ROOT / "backup_manager_port.py"
    )

    text = source.read_text(
        encoding="utf-8"
    )

    assert "def create_backup(" in text
    assert "def restore_backup(" in text
    assert "def verify_backup(" in text

    assert "def cleanup_backups(" not in text
    assert "def get_backup_metadata(" not in text
    assert "def get_cached_backup_reference(" not in text


def test_backup_manager_does_not_import_recovery_manager():
    """Chunk 13: dependency direction is Recovery Manager ->
    BackupManagerPort -> Backup Manager, never reversed."""
    tree = read_tree(
        "backup_manager.py"
    )

    assert (
        "recovery_manager"
        not in imported_modules(tree)
    )


def test_backup_storage_does_not_import_recovery_manager():
    """Chunk 13: storage sits below Backup Manager and must
    never reach up to Recovery Manager."""
    tree = read_tree(
        "filesystem_backup_storage.py"
    )

    assert (
        "recovery_manager"
        not in imported_modules(tree)
    )


def test_recovery_backup_integration_depends_on_backup_port():
    """Chunk 13: Recovery integration talks through the
    BackupManagerPort contract."""
    tree = read_tree(
        "recovery_backup_integration.py"
    )

    imported = imported_modules(tree)

    assert "backup_manager_port" in imported


def test_recovery_backup_integration_does_not_import_storage():
    """Chunk 13: integration must not reach around the
    Backup Manager into Backup Storage."""
    tree = read_tree(
        "recovery_backup_integration.py"
    )

    imported = imported_modules(tree)

    assert (
        "filesystem_backup_storage"
        not in imported
    )


def test_backup_manager_uses_security_context():
    """Chunk 13: access control, encryption, and secure
    deletion remain injected security boundaries."""
    source = (
        ROOT / "backup_manager.py"
    )

    text = source.read_text(
        encoding="utf-8"
    )

    assert "BackupSecurityContext" in text
    assert "BackupSecurityOperation" in text


def test_backup_manager_does_not_hardcode_retention_or_retry_policy():
    """Chunk 13: the source specifies retry and expired-backup
    cleanup, but prescribes no numeric policy - neither may
    the implementation invent one."""
    source = (
        ROOT / "backup_manager.py"
    )

    text = source.read_text(
        encoding="utf-8"
    ).lower()

    forbidden = {
        "retention_days",
        "expiration_days",
        "expiry_days",
        "retry_count = 3",
        "retry_count = 5",
        "max_attempts=3",
        "max_attempts=5",
    }

    for token in forbidden:
        assert token not in text


def test_backup_manager_contains_required_core_operations():
    """Chunk 13: Backup Manager owns the backup lifecycle:
    create, restore, verify, and cleanup."""
    source = (
        ROOT / "backup_manager.py"
    )

    text = source.read_text(
        encoding="utf-8"
    )

    required = (
        "create_backup",
        "restore_backup",
        "verify_backup",
        "cleanup_backups",
    )

    for symbol in required:
        assert symbol in text


def test_backup_manager_does_not_contain_ml_or_anomaly_operations():
    """Chunk 13: no ML or anomaly-detection operation may
    appear in Backup Manager."""
    source = (
        ROOT / "backup_manager.py"
    )

    text = source.read_text(
        encoding="utf-8"
    )

    forbidden = (
        "predict_anomaly",
        "train_model",
        "calculate_anomaly_score",
        "build_candidate_pattern",
        "detect_drift",
    )

    for symbol in forbidden:
        assert symbol not in text


def test_end_to_end_recovery_uses_concrete_backup_manager(
    tmp_path: Path,
):
    """Chunk 13: real wiring proof - Recovery Manager ->
    BackupManagerPort -> BackupManager ->
    FilesystemBackupStorage -> real filesystem."""
    manager = build_real_manager(
        tmp_path
    )

    assert isinstance(
        manager,
        BackupManagerPort,
    )

    source = tmp_path / "architecture.txt"

    source.write_text(
        "original",
        encoding="utf-8",
    )

    policy = RecoveryPolicy(
        policy_id="restore-policy",
        action=RecoveryAction.RESTORE_PREVIOUS_VERSION,
    )

    metadata = build_file_metadata(
        source
    )

    reference = manager.create_backup(
        metadata,
        policy,
    )

    source.write_text(
        "modified",
        encoding="utf-8",
    )

    assert manager.verify_backup(
        reference
    ) is True

    assert manager.restore_backup(
        reference,
        metadata,
    ) is True

    assert source.read_text(
        encoding="utf-8"
    ) == "original"
