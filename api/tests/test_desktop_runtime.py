from pathlib import Path
from sqlalchemy import create_engine, inspect, text


def test_settings_accept_json_encoded_desktop_lists(monkeypatch):
    from app.core.config import Settings

    monkeypatch.setenv("FRONTEND_ORIGIN", "http://127.0.0.1:43124")
    monkeypatch.setenv("ALLOWED_SCAN_TARGETS", '["localhost","127.0.0.1","::1"]')

    configured = Settings()

    assert configured.frontend_origin == "http://127.0.0.1:43124"
    assert configured.allowed_scan_targets == ["localhost", "127.0.0.1", "::1"]


def test_settings_reject_empty_required_values(monkeypatch):
    from app.core.config import Settings
    from pydantic import ValidationError
    import pytest

    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("JWT_SECRET", "")

    with pytest.raises(ValidationError, match="obrigat"):
        Settings()


def test_desktop_database_url_uses_user_data_directory(tmp_path: Path):
    from app.desktop import build_desktop_environment

    environment = build_desktop_environment(tmp_path, port=43123)

    assert environment["DATABASE_URL"] == (
        f"sqlite+pysqlite:///{(tmp_path / 'sentinelkit.db').as_posix()}"
    )
    assert environment["CELERY_TASK_ALWAYS_EAGER"] == "true"
    assert environment["API_HOST"] == "127.0.0.1"
    assert environment["API_PORT"] == "43123"
    assert environment["FRONTEND_ORIGIN"] == "http://127.0.0.1"


def test_desktop_runtime_runs_migrations_on_empty_database(tmp_path: Path):
    from app.desktop import upgrade_desktop_database

    database_path = tmp_path / "sentinelkit.db"
    upgrade_desktop_database(database_path)

    engine = create_engine(f"sqlite+pysqlite:///{database_path.as_posix()}")
    tables = set(inspect(engine).get_table_names())
    revision = engine.execute if False else None
    with engine.connect() as connection:
        version = connection.scalar(text("select version_num from alembic_version"))
    engine.dispose()

    assert "users" in tables
    assert version == "0002"


def test_desktop_migration_upgrade_is_idempotent(tmp_path: Path):
    from app.desktop import upgrade_desktop_database

    database_path = tmp_path / "sentinelkit.db"
    upgrade_desktop_database(database_path)
    upgrade_desktop_database(database_path)

    engine = create_engine(f"sqlite+pysqlite:///{database_path.as_posix()}")
    with engine.connect() as connection:
        versions = connection.execute(text("select version_num from alembic_version")).all()
    engine.dispose()

    assert versions == [("0002",)]


def test_desktop_migration_adds_required_name_to_existing_database(tmp_path: Path):
    from alembic import command
    from alembic.config import Config
    from app.desktop import upgrade_desktop_database

    database_path = tmp_path / "sentinelkit.db"
    api_root = Path(__file__).resolve().parents[1]
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option("script_location", str(api_root / "alembic"))
    config.attributes["database_url"] = (
        f"sqlite+pysqlite:///{database_path.as_posix()}"
    )
    command.upgrade(config, "0001_initial")

    engine = create_engine(f"sqlite+pysqlite:///{database_path.as_posix()}")
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users (email, password_hash, created_at, updated_at) "
                "VALUES ('legacy@example.com', 'hash', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
    engine.dispose()

    upgrade_desktop_database(database_path)

    engine = create_engine(f"sqlite+pysqlite:///{database_path.as_posix()}")
    columns = {column["name"]: column for column in inspect(engine).get_columns("users")}
    with engine.connect() as connection:
        name = connection.scalar(
            text("SELECT name FROM users WHERE email = 'legacy@example.com'")
        )
        version = connection.scalar(text("SELECT version_num FROM alembic_version"))
    engine.dispose()

    assert columns["name"]["nullable"] is False
    assert name == "legacy"
    assert version == "0002"


def test_desktop_migration_adopts_legacy_database_without_alembic_version(
    tmp_path: Path,
):
    from alembic import command
    from alembic.config import Config
    from app.desktop import upgrade_desktop_database

    database_path = tmp_path / "sentinelkit.db"
    api_root = Path(__file__).resolve().parents[1]
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option("script_location", str(api_root / "alembic"))
    config.attributes["database_url"] = (
        f"sqlite+pysqlite:///{database_path.as_posix()}"
    )
    command.upgrade(config, "0001_initial")

    engine = create_engine(f"sqlite+pysqlite:///{database_path.as_posix()}")
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users (email, password_hash, created_at, updated_at) "
                "VALUES ('legacy@example.com', 'hash', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
        connection.execute(text("DELETE FROM alembic_version"))
    engine.dispose()

    upgrade_desktop_database(database_path)

    engine = create_engine(f"sqlite+pysqlite:///{database_path.as_posix()}")
    with engine.connect() as connection:
        name = connection.scalar(
            text("SELECT name FROM users WHERE email = 'legacy@example.com'")
        )
        version = connection.scalar(text("SELECT version_num FROM alembic_version"))
    engine.dispose()

    assert name == "legacy"
    assert version == "0002"
