from unittest.mock import MagicMock
import pytest
from pymongo.errors import AutoReconnect
import database


@pytest.fixture
def persistence_with_mock_client(monkeypatch):
    client = MagicMock()
    factory = MagicMock(return_value=client)
    monkeypatch.setattr(database, "MongoClient", factory)
    persistence = database.MongoDBPersistence(
        connection_string="mongodb://test:27017/",
        database_name="test_database",
        server_selection_timeout_ms=1000,
    )
    return persistence, client, factory


def test_constructor_does_not_ping_database(
    persistence_with_mock_client,
):
    persistence, client, _ = persistence_with_mock_client
    client.admin.command.assert_not_called()


def test_verify_connection_sends_ping(
    persistence_with_mock_client,
):
    persistence, client, _ = persistence_with_mock_client
    persistence.verify_connection()
    client.admin.command.assert_called_once_with("ping")


def test_verify_connection_raises_on_closed_client(
    persistence_with_mock_client,
):
    persistence, client, _ = persistence_with_mock_client
    persistence.close()
    with pytest.raises(RuntimeError, match="already closed"):
        persistence.verify_connection()


def test_close_is_idempotent(
    persistence_with_mock_client,
):
    persistence, client, _ = persistence_with_mock_client
    persistence.close()
    client.close.assert_called_once()
    persistence.close()
    client.close.assert_called_once()


def test_save_methods_raise_on_closed_client(
    persistence_with_mock_client,
):
    persistence, client, _ = persistence_with_mock_client
    persistence.close()

    with pytest.raises(RuntimeError, match="already closed"):
        persistence.save_event({"test": "data"})

    with pytest.raises(RuntimeError, match="already closed"):
        persistence.save_baseline_entry({"test": "data"})

    with pytest.raises(RuntimeError, match="already closed"):
        persistence.save_directory_snapshot({"test": "data"})

    with pytest.raises(RuntimeError, match="already closed"):
        persistence.save_validation_result({"test": "data"})

    with pytest.raises(RuntimeError, match="already closed"):
        persistence.save_watcher_registration({"test": "data"})


def test_context_manager_ensures_open(
    persistence_with_mock_client,
):
    persistence, client, _ = persistence_with_mock_client
    with persistence as p:
        assert p is persistence
        p.verify_connection()
    client.close.assert_called_once()


def test_context_manager_closes_on_exit(
    persistence_with_mock_client,
):
    persistence, client, _ = persistence_with_mock_client
    with persistence:
        pass
    client.close.assert_called_once()


def test_context_manager_does_not_suppress_exceptions(
    persistence_with_mock_client,
):
    persistence, client, _ = persistence_with_mock_client
    with pytest.raises(ValueError):
        with persistence:
            raise ValueError("test error")
    client.close.assert_called_once()


def test_context_manager_fails_on_already_closed(
    persistence_with_mock_client,
):
    persistence, client, _ = persistence_with_mock_client
    persistence.close()
    with pytest.raises(RuntimeError, match="already closed"):
        with persistence:
            pass


def test_get_default_persistence_returns_singleton():
    p1 = database.get_default_persistence()
    p2 = database.get_default_persistence()
    assert p1 is p2


def test_close_default_persistence_closes_singleton(monkeypatch):
    mock_persistence = MagicMock()
    monkeypatch.setattr(
        database,
        "_default_persistence",
        mock_persistence,
    )
    database.close_default_persistence()
    mock_persistence.close.assert_called_once()
