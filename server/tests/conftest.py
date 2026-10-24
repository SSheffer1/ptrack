import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from ptrack.auth import create_user, issue_token
from ptrack.db import get_session
from ptrack.main import app
from ptrack.models import User

PASSWORD = "correct horse battery"


@pytest.fixture
def engine():
    # A fresh in-memory database per test. Not using `with TestClient(...)` skips
    # the app's startup hook, so the real ptrack.db file is never touched.
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)

    def session_override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    yield engine
    app.dependency_overrides.clear()


@pytest.fixture
def sign_in(engine):
    """sign_in("bob") → a client signed in as bob (the account is created if needed)."""
    users: dict[str, str] = {}

    def make(username: str, admin: bool = False) -> TestClient:
        with Session(engine) as session:
            if username not in users:
                users[username] = create_user(session, username, username.title(), PASSWORD, admin).id
                session.flush()
            token = issue_token(session, session.get(User, users[username]), f"{username}'s test device")
            session.commit()
        c = TestClient(app, base_url="http://testserver/api", headers={"Authorization": f"Bearer {token}"})
        c.user_id = users[username]  # type: ignore[attr-defined]
        return c

    return make


@pytest.fixture
def client(sign_in):
    """Signed in as alice, an admin."""
    return sign_in("alice", admin=True)


@pytest.fixture
def bob(sign_in):
    return sign_in("bob")


@pytest.fixture
def anon(engine):
    return TestClient(app, base_url="http://testserver/api")


@pytest.fixture
def home(client):
    """A HOME project (owned by alice) to put tickets in."""
    return client.post("/projects", json={"key": "HOME", "name": "Home"}).json()
