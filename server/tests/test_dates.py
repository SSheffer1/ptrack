"""Assigned and completed dates."""

from datetime import date, datetime, timedelta

TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)


def new(client, title="Homework", **extra):
    r = client.post("/items", json={"project": "HOME", "title": title, **extra})
    assert r.status_code == 201, r.text
    return r.json()


def test_assigned_defaults_to_created_date(client, home):
    item = new(client)
    assert item["assigned_on"] is None
    assert item["assigned"] == TODAY.isoformat()


def test_assigned_can_be_backdated_and_reset(client, home):
    item = new(client, assigned_on="2026-10-19")
    assert item["assigned"] == "2026-10-19"
    reset = client.patch(f"/items/{item['key']}", json={"assigned_on": None}).json()
    assert reset["assigned"] == TODAY.isoformat()


def test_marking_done_records_completion_and_reopening_clears_it(client, home):
    item = new(client)
    assert item["completed_on"] is None
    done = client.patch("/items/HOME-1", json={"status": "done"}).json()
    assert done["completed_on"] == TODAY.isoformat()
    reopened = client.patch("/items/HOME-1", json={"status": "todo"}).json()
    assert reopened["completed_on"] is None


def test_completion_date_can_be_given_or_changed(client, home):
    new(client)
    done = client.patch("/items/HOME-1", json={"status": "done", "completed_on": YESTERDAY.isoformat()}).json()
    assert done["completed_on"] == YESTERDAY.isoformat()
    edited = client.patch("/items/HOME-1", json={"completed_on": "2026-10-01"}).json()
    assert edited["completed_on"] == "2026-10-01"


def test_offline_completion_uses_the_day_it_happened(client, home):
    # Created and finished on the phone days ago; synced only now.
    def ms(days_ago):
        return int((datetime.now() - timedelta(days=days_ago)).timestamp() * 1000)

    def change(field, value, ts):
        return {"entity": "item", "entity_id": "offline-1", "field": field, "value": value, "ts": ts}

    client.post("/sync", json={"device_id": "phone", "changes": [
        change("type", "ticket", ms(4)),
        change("project_id", home["id"], ms(4)),
        change("title", "Done on the bus", ms(4)),
        change("status", "done", ms(3)),
    ]})
    item = client.get("/items/offline-1").json()
    assert item["completed_on"] == (TODAY - timedelta(days=3)).isoformat()
    assert item["assigned"] == (TODAY - timedelta(days=4)).isoformat()


def test_sort_by_completed(client, home):
    for title in ["A", "B", "C"]:
        new(client, title)
    client.patch("/items/HOME-1", json={"status": "done", "completed_on": "2026-10-20"})
    client.patch("/items/HOME-2", json={"status": "done", "completed_on": "2026-10-22"})
    titles = [i["title"] for i in client.get("/items", params={"sort": "completed"}).json()]
    assert titles == ["B", "A", "C"]


def test_sort_by_due(client, home):
    new(client, "No date")
    new(client, "Later", due="2026-11-02")
    new(client, "Sooner, untimed", due="2026-11-01")
    new(client, "Sooner, morning", due="2026-11-01", due_time="09:00")
    titles = [i["title"] for i in client.get("/items", params={"sort": "due"}).json()]
    assert titles == ["Sooner, morning", "Sooner, untimed", "Later", "No date"]


def test_sort_by_project_priority_status_title(client, home):
    client.post("/projects", json={"key": "CAR", "name": "Car"})
    new(client, "wash", project="CAR", priority="low", status="blocked")
    new(client, "Bills", priority="urgent", due="2026-11-02", status="in_progress")
    new(client, "apples", priority="urgent", due="2026-11-01", status="backlog")
    new(client, "Cat food")

    def titles(sort):
        return [i["title"] for i in client.get("/items", params={"sort": sort}).json()]

    # Ties keep due-date order (undated last).
    assert titles("project") == ["wash", "apples", "Bills", "Cat food"]
    assert titles("priority") == ["apples", "Bills", "wash", "Cat food"]
    assert titles("status") == ["apples", "Cat food", "Bills", "wash"]
    assert titles("title") == ["apples", "Bills", "Cat food", "wash"]  # ignoring case


def test_completed_range_filter(client, home):
    for title, completed in [("Sept", "2026-09-30"), ("Oct", "2026-10-15"), ("Open", None)]:
        new(client, title)
        if completed:
            key = client.get("/items", params={"q": title}).json()[0]["key"]
            client.patch(f"/items/{key}", json={"status": "done", "completed_on": completed})
    params = {"completed_from": "2026-10-01", "completed_to": "2026-10-31"}
    assert [i["title"] for i in client.get("/items", params=params).json()] == ["Oct"]
