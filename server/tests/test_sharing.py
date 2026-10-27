"""Shared projects: owners, editors, assignees, and what sync shows each person."""

import uuid

import pytest
from sqlmodel import Session
from test_sync import change, new_ticket, sync

from ptrack.admin import _set_role
from ptrack.models import Role


def share(owner, key, username):
    r = owner.post(f"/projects/{key}/members", json={"username": username})
    assert r.status_code == 201, r.text
    return r.json()


def test_projects_are_private(client, bob, home):
    client.post("/items", json={"project": "HOME", "title": "Alice's ticket"})
    assert bob.get("/projects").json() == []
    assert bob.get("/items").json() == []
    assert bob.get("/items/HOME-1").status_code == 404
    assert bob.post("/items", json={"project": "HOME", "title": "x"}).status_code == 404
    assert sync(bob, "bob-phone")["changes"] == []


def test_project_keys_are_unique_across_users(client, bob, home):
    assert bob.post("/projects", json={"key": "HOME", "name": "Bob's home"}).status_code == 409


def test_editor_can_create_edit_and_comment(client, bob, home):
    client.post("/items", json={"project": "HOME", "title": "Fix sink"})
    share(client, "HOME", "bob")
    assert [(p["key"], p["role"]) for p in bob.get("/projects").json()] == [("HOME", "editor")]

    assert bob.patch("/items/HOME-1", json={"status": "in_progress"}).status_code == 200
    assert bob.post("/items/HOME-1/comments", json={"body": "on it"}).status_code == 201
    made = bob.post("/items", json={"project": "HOME", "title": "Buy washers"}).json()
    assert (made["key"], made["created_by"]) == ("HOME-2", bob.user_id)

    history = client.get("/items/HOME-1/history").json()
    assert {c["user_id"] for c in history if c["field"] == "status"} == {client.user_id, bob.user_id}


def test_only_the_owner_deletes_renames_and_manages(client, bob, sign_in, home):
    sign_in("carol")
    client.post("/items", json={"project": "HOME", "title": "Fix sink"})
    share(client, "HOME", "bob")

    assert bob.delete("/items/HOME-1").status_code == 403
    assert bob.patch("/projects/HOME", json={"name": "Bob's now"}).status_code == 403
    assert bob.delete("/projects/HOME").status_code == 403
    assert bob.post("/projects/HOME/members", json={"username": "carol"}).status_code == 403

    assert client.patch("/projects/HOME", json={"name": "Our home"}).json()["name"] == "Our home"
    assert client.delete("/items/HOME-1").status_code == 204


def test_an_admin_editor_may_delete_tickets(client, bob, sign_in):
    dana = sign_in("dana", admin=True)
    bob.post("/projects", json={"key": "BOBS", "name": "Bob's"})
    bob.post("/items", json={"project": "BOBS", "title": "Fix bike"})
    bob.post("/items", json={"project": "BOBS", "title": "Oil chain"})
    share(bob, "BOBS", "dana")

    assert dana.delete("/items/BOBS-1").status_code == 204  # admin, though only an editor
    assert client.delete("/items/BOBS-2").status_code == 404  # admins still only see their own projects
    assert dana.patch("/projects/BOBS", json={"name": "Dana's"}).status_code == 403  # the project stays bob's


def test_assign_to_a_member_only(client, bob, sign_in, home):
    carol = sign_in("carol")
    client.post("/items", json={"project": "HOME", "title": "Mow lawn"})
    assert client.patch("/items/HOME-1", json={"assignee_id": bob.user_id}).status_code == 403  # not a member yet
    share(client, "HOME", "bob")
    assert client.patch("/items/HOME-1", json={"assignee_id": bob.user_id}).json()["assignee_id"] == bob.user_id
    assert client.patch("/items/HOME-1", json={"assignee_id": carol.user_id}).status_code == 403

    mine = [i["title"] for i in bob.get("/items", params={"assignee": "me"}).json()]
    assert mine == ["Mow lawn"]
    assert client.get("/items", params={"assignee": "me"}).json() == []


def test_the_assignee_controls_reminders(client, bob, home):
    client.post("/items", json={"project": "HOME", "title": "Mow lawn", "due": "2026-11-01", "reminders": ["-1d"]})
    share(client, "HOME", "bob")
    assert bob.patch("/items/HOME-1", json={"reminders": []}).status_code == 403  # alice's (creator's) for now
    client.patch("/items/HOME-1", json={"assignee_id": bob.user_id})
    assert client.patch("/items/HOME-1", json={"reminders": []}).status_code == 403  # now bob's
    assert bob.patch("/items/HOME-1", json={"reminders": ["-8h"]}).json()["reminders"] == ["-8h"]


def test_joining_a_project_resets_sync_and_brings_its_history(client, bob, home):
    client.post("/items", json={"project": "HOME", "title": "Old ticket"})
    first = sync(bob, "bob-phone")
    assert (first["reset"], first["epoch"], first["changes"]) == (False, 0, [])

    share(client, "HOME", "bob")
    second = sync(bob, "bob-phone", since=first["cursor"], epoch=first["epoch"])
    assert second["reset"] is True and second["epoch"] == 1
    titles = [c["value"] for c in second["changes"] if c["field"] == "title"]
    assert titles == ["Old ticket"]
    assert {(m["user_id"], m["role"]) for m in second["members"]} == {(client.user_id, "owner"), (bob.user_id, "editor")}
    assert {u["username"] for u in second["users"]} == {"alice", "bob"}


def test_leaving_unassigns_and_hides_the_project(client, bob, home):
    client.post("/items", json={"project": "HOME", "title": "Mow lawn"})
    share(client, "HOME", "bob")
    client.patch("/items/HOME-1", json={"assignee_id": bob.user_id})
    first = sync(bob, "bob-phone", epoch=1)

    assert bob.delete(f"/projects/HOME/members/{bob.user_id}").status_code == 204
    assert client.get("/items/HOME-1").json()["assignee_id"] is None
    assert bob.get("/projects").json() == []

    after = sync(bob, "bob-phone", since=first["cursor"], epoch=1)
    assert after["reset"] is True and after["changes"] == []


def test_offline_edits_after_removal_are_dropped(client, bob, home):
    item = client.post("/items", json={"project": "HOME", "title": "Mow lawn"}).json()
    share(client, "HOME", "bob")
    client.delete(f"/projects/HOME/members/{bob.user_id}")
    # Bob's phone was offline and didn't know; its edit comes in later.
    result = sync(bob, "bob-phone", [change(item["id"], "title", "Bob's edit", 10**13)], epoch=1)
    assert [d["reason"] for d in result["dropped"]] == ["you're not a member of this project"]
    assert client.get("/items/HOME-1").json()["title"] == "Mow lawn"


def test_owner_cannot_leave_their_own_project(client, home):
    assert client.delete(f"/projects/HOME/members/{client.user_id}").status_code == 400


def test_same_key_created_offline_by_two_people_gets_renamed(client, bob):
    alice_gym, bob_gym = str(uuid.uuid4()), str(uuid.uuid4())
    sync(client, "alice-phone", [change(alice_gym, "key", "GYM", 1000, "project"), change(alice_gym, "name", "Gym", 1000, "project")])
    sync(bob, "bob-phone", [change(bob_gym, "key", "GYM", 2000, "project"), change(bob_gym, "name", "Bob's gym", 2000, "project")])
    assert [p["key"] for p in client.get("/projects").json()] == ["GYM"]
    assert [p["key"] for p in bob.get("/projects").json()] == ["GYM2"]


def test_recurring_copy_keeps_assignee_and_creator(client, bob, home):
    share(client, "HOME", "bob")
    client.post("/items", json={"project": "HOME", "title": "Trash out", "due": "2099-01-05", "repeat": "FREQ=WEEKLY",
                                "assignee_id": bob.user_id})
    done = bob.patch("/items/HOME-1", json={"status": "done"}).json()
    nxt = client.get(f"/items/{done['next_id']}").json()
    assert (nxt["assignee_id"], nxt["created_by"], nxt["key"]) == (bob.user_id, client.user_id, "HOME-2")


def test_ticket_created_by_phone_records_creator(client, home):
    item_id, changes = new_ticket(home["id"], "From the phone", ts=1000)
    sync(client, "phone", changes)
    assert client.get(f"/items/{item_id}").json()["created_by"] == client.user_id


def test_comment_edit_and_delete_permissions(client, bob, sign_in, home):
    carol = sign_in("carol")
    client.post("/items", json={"project": "HOME", "title": "Fix sink"})
    share(client, "HOME", "bob")
    share(client, "HOME", "carol")
    bobs = bob.post("/items/HOME-1/comments", json={"body": "on it"}).json()
    assert bobs["edited"] is False

    # Bob edits his own comment; it's marked edited.
    edited = bob.patch(f"/items/HOME-1/comments/{bobs['id']}", json={"body": "on it, tomorrow"}).json()
    assert (edited["body"], edited["edited"]) == ("on it, tomorrow", True)

    # Nobody else rewords it, not even the owner; another editor can't delete it.
    assert client.patch(f"/items/HOME-1/comments/{bobs['id']}", json={"body": "nope"}).status_code == 403
    assert carol.delete(f"/items/HOME-1/comments/{bobs['id']}").status_code == 403
    assert bob.patch(f"/items/HOME-1/comments/{bobs['id']}", json={"body": ""}).status_code == 422

    # The owner can delete it; then it's gone.
    assert client.delete(f"/items/HOME-1/comments/{bobs['id']}").status_code == 204
    assert client.get("/items/HOME-1/comments").json() == []
    assert bob.delete(f"/items/HOME-1/comments/{bobs['id']}").status_code == 404


def test_authors_delete_their_own_comments(client, bob, home):
    client.post("/items", json={"project": "HOME", "title": "Fix sink"})
    share(client, "HOME", "bob")
    c = bob.post("/items/HOME-1/comments", json={"body": "oops"}).json()
    assert bob.delete(f"/items/HOME-1/comments/{c['id']}").status_code == 204
    assert client.get("/items/HOME-1/comments").json() == []


def test_admin_command_sets_roles(engine, client, bob, sign_in, home):
    client.post("/items", json={"project": "HOME", "title": "Fix sink"})
    share(client, "HOME", "bob")
    sign_in("carol")
    with Session(engine) as session:
        assert _set_role(session, "home", "bob", Role.owner) == "bob is now owner of HOME"
        assert _set_role(session, "HOME", "carol", Role.editor) == "added carol to HOME as editor"
        session.commit()
    assert bob.patch("/projects/HOME", json={"name": "Our home"}).status_code == 200  # bob owns it too now
    assert bob.delete("/items/HOME-1").status_code == 204

    with Session(engine) as session:
        _set_role(session, "HOME", "alice", Role.editor)  # fine: bob is still an owner
        session.commit()
        with pytest.raises(SystemExit, match="only owner"):
            _set_role(session, "HOME", "bob", Role.editor)
