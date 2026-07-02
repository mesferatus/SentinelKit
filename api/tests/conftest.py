import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///./sentinelkit-test.db")
os.environ.setdefault("JWT_SECRET", "test-access-secret-with-at-least-32-characters")
os.environ.setdefault("JWT_REFRESH_SECRET", "test-refresh-secret-with-at-least-32-characters")

from app.core.database import Base, get_db
from app.main import app


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(session_factory) -> Generator[TestClient, None, None]:
    def override_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.state.limiter._storage.reset()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    app.state.limiter._storage.reset()
