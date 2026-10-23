import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from ptrack.db import get_session
from ptrack.main import app


@pytest.fixture
def client():
    # A fresh in-memory database per test. Not using `with TestClient(...)` skips
    # the app's startup hook, so the real ptrack.db file is never touched.
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)

    def session_override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def home(client):
    """A HOME project to put tickets in."""
    return client.post("/projects", json={"key": "HOME", "name": "Home"}).json()
