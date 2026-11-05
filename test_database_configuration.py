from unittest.mock import MagicMock, patch
import pytest

from database import (
    DEFAULT_MONGODB_DATABASE,
    DEFAULT_MONGODB_SERVER_SELECTION_TIMEOUT_MS,
    DEFAULT_MONGODB_URI,
    MongoDBPersistence,
)


@pytest.fixture(autouse=True)
def mock_mongo_client():
    with patch("database.MongoClient") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        yield mock_client


def test_default_configuration(monkeypatch, mock_mongo_client):
    monkeypatch.delenv("PRISM_MONGODB_URI", raising=False)
    monkeypatch.delenv("PRISM_MONGODB_DATABASE", raising=False)
    monkeypatch.delenv("PRISM_MONGODB_SERVER_SELECTION_TIMEOUT_MS", raising=False)

    persistence = MongoDBPersistence()

    assert persistence._connection_string == DEFAULT_MONGODB_URI
    assert persistence._database_name == DEFAULT_MONGODB_DATABASE
    assert persistence._server_selection_timeout_ms == DEFAULT_MONGODB_SERVER_SELECTION_TIMEOUT_MS
    mock_mongo_client.assert_called_once_with(
        DEFAULT_MONGODB_URI,
        serverSelectionTimeoutMS=DEFAULT_MONGODB_SERVER_SELECTION_TIMEOUT_MS,
    )


def test_environment_uri(monkeypatch, mock_mongo_client):
    monkeypatch.setenv("PRISM_MONGODB_URI", "mongodb://custom:27017/")
    monkeypatch.delenv("PRISM_MONGODB_DATABASE", raising=False)
    monkeypatch.delenv("PRISM_MONGODB_SERVER_SELECTION_TIMEOUT_MS", raising=False)

    persistence = MongoDBPersistence()

    assert persistence._connection_string == "mongodb://custom:27017/"
    mock_mongo_client.assert_called_once_with(
        "mongodb://custom:27017/",
        serverSelectionTimeoutMS=DEFAULT_MONGODB_SERVER_SELECTION_TIMEOUT_MS,
    )


def test_environment_database(monkeypatch, mock_mongo_client):
    monkeypatch.delenv("PRISM_MONGODB_URI", raising=False)
    monkeypatch.setenv("PRISM_MONGODB_DATABASE", "custom_db")
    monkeypatch.delenv("PRISM_MONGODB_SERVER_SELECTION_TIMEOUT_MS", raising=False)

    persistence = MongoDBPersistence()

    assert persistence._database_name == "custom_db"


def test_environment_timeout(monkeypatch, mock_mongo_client):
    monkeypatch.delenv("PRISM_MONGODB_URI", raising=False)
    monkeypatch.delenv("PRISM_MONGODB_DATABASE", raising=False)
    monkeypatch.setenv("PRISM_MONGODB_SERVER_SELECTION_TIMEOUT_MS", "3000")

    persistence = MongoDBPersistence()

    assert persistence._server_selection_timeout_ms == 3000
    mock_mongo_client.assert_called_once_with(
        DEFAULT_MONGODB_URI,
        serverSelectionTimeoutMS=3000,
    )


def test_explicit_constructor_arguments(monkeypatch, mock_mongo_client):
    monkeypatch.setenv("PRISM_MONGODB_URI", "mongodb://env:27017/")
    monkeypatch.setenv("PRISM_MONGODB_DATABASE", "env_db")
    monkeypatch.setenv("PRISM_MONGODB_SERVER_SELECTION_TIMEOUT_MS", "9999")

    persistence = MongoDBPersistence(
        connection_string="mongodb://explicit:27017/",
        database_name="explicit_db",
        server_selection_timeout_ms=1234,
    )

    assert persistence._connection_string == "mongodb://explicit:27017/"
    assert persistence._database_name == "explicit_db"
    assert persistence._server_selection_timeout_ms == 1234
    mock_mongo_client.assert_called_once_with(
        "mongodb://explicit:27017/",
        serverSelectionTimeoutMS=1234,
    )


@pytest.mark.parametrize("empty_uri", ["", "   "])
def test_empty_uri_explicit(empty_uri):
    with pytest.raises(ValueError, match="PRISM_MONGODB_URI must be a non-empty string"):
        MongoDBPersistence(connection_string=empty_uri)


@pytest.mark.parametrize("empty_uri", ["", "   "])
def test_empty_uri_environment(monkeypatch, empty_uri):
    monkeypatch.setenv("PRISM_MONGODB_URI", empty_uri)
    with pytest.raises(ValueError, match="PRISM_MONGODB_URI must be a non-empty string"):
        MongoDBPersistence()


@pytest.mark.parametrize("empty_db", ["", "   "])
def test_empty_database_explicit(empty_db):
    with pytest.raises(ValueError, match="PRISM_MONGODB_DATABASE must be a non-empty string"):
        MongoDBPersistence(database_name=empty_db)


@pytest.mark.parametrize("empty_db", ["", "   "])
def test_empty_database_environment(monkeypatch, empty_db):
    monkeypatch.setenv("PRISM_MONGODB_DATABASE", empty_db)
    with pytest.raises(ValueError, match="PRISM_MONGODB_DATABASE must be a non-empty string"):
        MongoDBPersistence()


def test_invalid_timeout_string_explicit():
    with pytest.raises(ValueError, match="PRISM_MONGODB_SERVER_SELECTION_TIMEOUT_MS must be a positive integer"):
        MongoDBPersistence(server_selection_timeout_ms="invalid")


def test_invalid_timeout_string_environment(monkeypatch):
    monkeypatch.setenv("PRISM_MONGODB_SERVER_SELECTION_TIMEOUT_MS", "not_a_number")
    with pytest.raises(ValueError, match="PRISM_MONGODB_SERVER_SELECTION_TIMEOUT_MS must be a positive integer"):
        MongoDBPersistence()


@pytest.mark.parametrize("zero_or_neg", [0, -100])
def test_zero_or_negative_timeout_explicit(zero_or_neg):
    with pytest.raises(ValueError, match="PRISM_MONGODB_SERVER_SELECTION_TIMEOUT_MS must be a positive integer"):
        MongoDBPersistence(server_selection_timeout_ms=zero_or_neg)


@pytest.mark.parametrize("zero_or_neg", ["0", "-500"])
def test_zero_or_negative_timeout_environment(monkeypatch, zero_or_neg):
    monkeypatch.setenv("PRISM_MONGODB_SERVER_SELECTION_TIMEOUT_MS", zero_or_neg)
    with pytest.raises(ValueError, match="PRISM_MONGODB_SERVER_SELECTION_TIMEOUT_MS must be a positive integer"):
        MongoDBPersistence()


@pytest.mark.parametrize("bool_timeout", [True, False])
def test_boolean_constructor_timeout(bool_timeout):
    with pytest.raises(ValueError, match="PRISM_MONGODB_SERVER_SELECTION_TIMEOUT_MS must be a positive integer"):
        MongoDBPersistence(server_selection_timeout_ms=bool_timeout)
