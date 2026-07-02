from __future__ import annotations

import os
import sys
from pathlib import Path


def build_desktop_environment(user_data_path: Path, port: int) -> dict[str, str]:
    database_path = (user_data_path / "sentinelkit.db").resolve()
    return {
        "DATABASE_URL": f"sqlite+pysqlite:///{database_path.as_posix()}",
        "CELERY_TASK_ALWAYS_EAGER": "true",
        "API_HOST": "127.0.0.1",
        "API_PORT": str(port),
        "FRONTEND_ORIGIN": "http://127.0.0.1",
    }


def _resource_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))


def upgrade_desktop_database(database_path: Path) -> None:
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, inspect, text

    database_path.parent.mkdir(parents=True, exist_ok=True)
    database_url = f"sqlite+pysqlite:///{database_path.resolve().as_posix()}"
    root = _resource_root()
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    config.attributes["database_url"] = database_url

    if database_path.exists():
        engine = create_engine(database_url)
        try:
            tables = set(inspect(engine).get_table_names())
            has_revision = False
            if "alembic_version" in tables:
                with engine.connect() as connection:
                    has_revision = (
                        connection.scalar(
                            text("SELECT COUNT(*) FROM alembic_version")
                        )
                        or 0
                    ) > 0
        finally:
            engine.dispose()
        if "users" in tables and not has_revision:
            command.stamp(config, "0001_initial")

    command.upgrade(config, "head")


def main() -> None:
    import uvicorn

    database_url = os.environ.get("DATABASE_URL", "")
    if database_url.startswith("sqlite"):
        database_path = Path(database_url.removeprefix("sqlite+pysqlite:///"))
        upgrade_desktop_database(database_path)

    from app.main import app

    uvicorn.run(
        app,
        host=os.environ.get("API_HOST", "127.0.0.1"),
        port=int(os.environ.get("API_PORT", "8000")),
        log_level=os.environ.get("LOG_LEVEL", "info").lower(),
    )


if __name__ == "__main__":
    main()
