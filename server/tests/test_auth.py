from fastapi.testclient import TestClient

from conftest import PASSWORD
from ptrack.auth import hash_password, verify_password
from ptrack.main import app


def test_password_hashing():
    stored = hash_password("hunter22!")
    assert stored.startswith("scrypt$") and "hunter22" not in stored
    assert verify_password("hunter22!", stored)
    assert not verify_password("hunter23!", stored)
    assert not verify_password("anything", "")  # no password set


def test_everything_needs_sign_in(anon):
    assert anon.get("/health").status_code == 200
    for path in ["/projects", "/items", "/me", "/users"]:
        assert anon.get(path).status_code == 401
    assert anon.post("/sync", json={"device_id": "x"}).status_code == 401
    bad = TestClient(app, base_url="http://testserver/api", headers={"Authorization": "Bearer nope"})
    assert bad.get("/me").status_code == 401


def test_login_logout(client, anon):
    r = anon.post("/auth/login", json={"username": "ALICE ", "password": PASSWORD, "device_name": "Pixel"})
    assert r.status_code == 200
    token = r.json()["token"]
    assert r.json()["user"]["username"] == "alice"
    phone = TestClient(app, base_url="http://testserver/api", headers={"Authorization": f"Bearer {token}"})
    assert phone.get("/me").json()["is_admin"] is True

    devices = phone.get("/me/devices").json()
    assert [d["name"] for d in devices if d["current"]] == ["Pixel"]
    assert phone.post("/auth/logout").status_code == 204
    assert phone.get("/me").status_code == 401
    assert client.get("/me").status_code == 200  # other devices stay signed in


def test_wrong_password(client, anon):
    r = anon.post("/auth/login", json={"username": "alice", "password": "nope"})
    assert r.status_code == 401


def test_sign_out_another_device(client, sign_in):
    other = sign_in("alice")
    other_id = next(d["id"] for d in other.get("/me/devices").json() if d["current"])
    assert client.delete(f"/me/devices/{other_id}").status_code == 204
    assert other.get("/me").status_code == 401


def test_change_password(client, anon):
    assert client.post("/me/password", json={"current": "wrong", "new": "brand new pw"}).status_code == 403
    assert client.post("/me/password", json={"current": PASSWORD, "new": "short"}).status_code == 422
    assert client.post("/me/password", json={"current": PASSWORD, "new": "brand new pw"}).status_code == 204
    assert anon.post("/auth/login", json={"username": "alice", "password": "brand new pw"}).status_code == 200


def test_admin_manages_accounts(client, bob, anon):
    r = client.post("/admin/users", json={"username": "carol", "display_name": "Carol", "password": "carols pw!"})
    assert r.status_code == 201
    carol_id = r.json()["id"]
    assert client.post("/admin/users", json={"username": "carol", "password": "whatever1"}).status_code == 409
    assert {u["username"] for u in client.get("/admin/users").json()} == {"alice", "bob", "carol"}

    # Reset her password, then disable the account.
    client.patch(f"/admin/users/{carol_id}", json={"password": "reset pw 123"})
    login = anon.post("/auth/login", json={"username": "carol", "password": "reset pw 123"})
    carol = TestClient(app, base_url="http://testserver/api", headers={"Authorization": f"Bearer {login.json()['token']}"})
    client.patch(f"/admin/users/{carol_id}", json={"disabled": True})
    assert carol.get("/me").status_code == 401
    assert anon.post("/auth/login", json={"username": "carol", "password": "reset pw 123"}).status_code == 401

    # Only admins, and admins can't lock themselves out.
    assert bob.get("/admin/users").status_code == 403
    assert client.patch(f"/admin/users/{client.user_id}", json={"disabled": True}).status_code == 400


def test_idle_devices_are_signed_out(client, engine, monkeypatch):
    from sqlmodel import Session, select

    from ptrack import auth
    from ptrack.models import DeviceToken

    monkeypatch.setattr(auth, "settings", auth.settings.__class__(device_idle_days=30))
    with Session(engine) as session:
        for d in session.exec(select(DeviceToken)).all():
            d.last_used_at -= 31 * auth.DAY_MS
        session.commit()
    assert client.get("/me").status_code == 401
