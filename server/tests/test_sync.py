"""Sync as the phone app will use it: upload field changes, download with a cursor."""

import uuid


def sync(client, device, changes=(), since=0):
    r = client.post("/sync", json={"device_id": device, "since": since, "changes": list(changes)})
    assert r.status_code == 200, r.text
    return r.json()


def change(entity_id, field, value, ts, entity="item"):
    return {"entity": entity, "entity_id": entity_id, "field": field, "value": value, "ts": ts}


def new_ticket(project_id, title, ts):
    """The changes a phone would make to create a ticket offline."""
    item_id = str(uuid.uuid4())
    return item_id, [
        change(item_id, "type", "ticket", ts),
        change(item_id, "project_id", project_id, ts),
        change(item_id, "title", title, ts),
    ]


def test_offline_ticket_gets_number_from_server(client, home):
    item_id, changes = new_ticket(home["id"], "Fix bike", ts=1000)
    result = sync(client, "phone", changes)

    numbers = [c for c in result["changes"] if c["entity_id"] == item_id and c["field"] == "number"]
    assert numbers[0]["value"] == 1
    assert numbers[0]["device_id"] == "server"
    assert client.get("/items/HOME-1").json()["title"] == "Fix bike"


def test_two_offline_phones_dont_collide_on_numbers(client, home):
    a, changes_a = new_ticket(home["id"], "From phone A", ts=1000)
    b, changes_b = new_ticket(home["id"], "From phone B", ts=2000)
    sync(client, "phone-a", changes_a)
    sync(client, "phone-b", changes_b)
    assert client.get(f"/items/{a}").json()["key"] == "HOME-1"
    assert client.get(f"/items/{b}").json()["key"] == "HOME-2"


def test_ticket_synced_before_its_project_gets_numbered_later(client):
    project_id = str(uuid.uuid4())
    item_id, changes = new_ticket(project_id, "Orphan for now", ts=1000)
    sync(client, "phone", changes)
    assert client.get(f"/items/{item_id}").json()["key"] is None

    sync(client, "phone", [change(project_id, "key", "GYM", 2000, "project"),
                           change(project_id, "name", "Gym", 2000, "project")])
    assert client.get(f"/items/{item_id}").json()["key"] == "GYM-1"


def test_last_write_wins_regardless_of_arrival_order(client, home):
    item_id, changes = new_ticket(home["id"], "Original", ts=1000)
    sync(client, "phone", changes)

    # Phone A edited at t=3000 but syncs last; phone B edited earlier at t=2000.
    sync(client, "phone-b", [change(item_id, "title", "B's title", 2000)])
    sync(client, "phone-a", [change(item_id, "title", "A's title", 3000)])
    assert client.get(f"/items/{item_id}").json()["title"] == "A's title"

    # A late-arriving older edit doesn't overwrite, but is kept in history.
    sync(client, "phone-c", [change(item_id, "title", "C's stale title", 2500)])
    assert client.get(f"/items/{item_id}").json()["title"] == "A's title"
    titles = [c["value"] for c in client.get(f"/items/{item_id}/history").json() if c["field"] == "title"]
    assert "C's stale title" in titles


def test_edits_to_different_fields_both_survive(client, home):
    item_id, changes = new_ticket(home["id"], "Fix bike", ts=1000)
    sync(client, "phone", changes)
    sync(client, "phone", [change(item_id, "status", "done", 2000)])
    client.patch(f"/items/{item_id}", json={"priority": "high"})  # web edit, later
    item = client.get(f"/items/{item_id}").json()
    assert (item["status"], item["priority"]) == ("done", "high")


def test_retried_upload_is_ignored(client, home):
    item_id, changes = new_ticket(home["id"], "Fix bike", ts=1000)
    first = sync(client, "phone", changes)
    second = sync(client, "phone", changes, since=first["cursor"])
    assert second["changes"] == []


def test_cursor_only_returns_new_changes(client, home):
    first = sync(client, "phone")
    client.post("/items", json={"project": "HOME", "title": "Made on the web"})
    second = sync(client, "phone", since=first["cursor"])
    fields = {c["field"] for c in second["changes"]}
    assert {"title", "number"} <= fields
    assert all(c["seq"] > first["cursor"] for c in second["changes"])


def test_rejects_server_only_fields(client, home):
    item_id, _ = new_ticket(home["id"], "x", ts=1000)
    r = client.post("/sync", json={"device_id": "phone", "changes": [change(item_id, "number", 99, 1000)]})
    assert r.status_code == 400


def test_bad_batch_is_rejected_whole(client, home):
    item_id, changes = new_ticket(home["id"], "Should not exist", ts=1000)
    changes.append(change(item_id, "status", "not-a-status", 1000))
    r = client.post("/sync", json={"device_id": "phone", "changes": changes})
    assert r.status_code == 400
    assert client.get(f"/items/{item_id}").status_code == 404


def test_reserved_device_ids(client):
    r = client.post("/sync", json={"device_id": "server", "changes": []})
    assert r.status_code == 400
