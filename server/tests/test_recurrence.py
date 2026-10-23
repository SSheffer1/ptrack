from datetime import date, timedelta

import pytest

from ptrack.recurrence import next_due, normalize_rule

# --- The date math -------------------------------------------------------------

FRI = date(2026, 10, 30)  # a Friday
EARLY = date(2026, 10, 1)  # a "today" well before FRI


def test_weekly():
    assert next_due("FREQ=WEEKLY", FRI, EARLY) == date(2026, 11, 6)


def test_every_two_weeks():
    assert next_due("FREQ=WEEKLY;INTERVAL=2", FRI, EARLY) == date(2026, 11, 13)


def test_weekday_rule_moves_to_that_weekday():
    assert next_due("FREQ=WEEKLY;BYDAY=MO", FRI, EARLY) == date(2026, 11, 2)


def test_monthly_on_the_first():
    assert next_due("FREQ=MONTHLY;BYMONTHDAY=1", FRI, EARLY) == date(2026, 11, 1)


def test_finished_late_skips_to_today_or_later():
    today = date(2026, 11, 25)  # a Wednesday, weeks after FRI
    assert next_due("FREQ=WEEKLY;BYDAY=FR", FRI, today) == date(2026, 11, 27)


def test_until_ends_the_repeat():
    assert next_due("FREQ=WEEKLY;UNTIL=20261101", FRI, EARLY) is None


def test_no_due_date_counts_from_today():
    assert next_due("FREQ=DAILY", None, EARLY) == EARLY + timedelta(days=1)


def test_normalize():
    assert normalize_rule("rrule:freq=weekly;byday=fr") == "FREQ=WEEKLY;BYDAY=FR"
    assert normalize_rule("  ") is None
    for bad in ["FREQ=SOMETIMES", "FREQ=WEEKLY;COUNT=3", "DTSTART:20260101\nRRULE:FREQ=DAILY", "hello"]:
        with pytest.raises(ValueError):
            normalize_rule(bad)


# --- Through the API -------------------------------------------------------------

# A due date safely in the future, so "finished late" logic doesn't kick in.
SOON = date.today() + timedelta(days=3)


def make_recurring(client, **extra):
    body = {"project": "HOME", "title": "Lab report", "labels": ["lab"], "priority": "high",
            "due": SOON.isoformat(), "due_time": "23:59", "repeat": "FREQ=WEEKLY", **extra}
    r = client.post("/items", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_completing_recurring_ticket_creates_next(client, home):
    first = make_recurring(client)
    done = client.patch(f"/items/{first['key']}", json={"status": "done"}).json()

    nxt = client.get(f"/items/{done['next_id']}").json()
    assert nxt["key"] == "HOME-2"
    assert nxt["status"] == "todo"
    assert nxt["due"] == (SOON + timedelta(weeks=1)).isoformat()
    assert (nxt["title"], nxt["labels"], nxt["priority"], nxt["due_time"], nxt["repeat"]) == (
        "Lab report", ["lab"], "high", "23:59:00", "FREQ=WEEKLY")


def test_reopening_and_redoing_does_not_duplicate(client, home):
    first = make_recurring(client)
    client.patch("/items/HOME-1", json={"status": "done"})
    client.patch("/items/HOME-1", json={"status": "todo"})
    client.patch("/items/HOME-1", json={"status": "done"})
    assert [i["key"] for i in client.get("/items").json()] == ["HOME-1", "HOME-2"]
    assert first["next_id"] is None  # only set after completion


def test_non_recurring_done_creates_nothing(client, home):
    client.post("/items", json={"project": "HOME", "title": "One-off"})
    client.patch("/items/HOME-1", json={"status": "done"})
    assert len(client.get("/items").json()) == 1


def test_invalid_repeat_rejected(client, home):
    r = client.post("/items", json={"project": "HOME", "title": "x", "repeat": "FREQ=WEEKLY;COUNT=2"})
    assert r.status_code == 400
    assert "UNTIL" in r.json()["detail"]


def test_phone_completion_spawns_on_sync(client, home):
    first = make_recurring(client)
    r = client.post("/sync", json={"device_id": "phone", "since": 0, "changes": [
        {"entity": "item", "entity_id": first["id"], "field": "status", "value": "done", "ts": 10**13}]})
    changes = r.json()["changes"]
    next_id = next(c["value"] for c in changes if c["field"] == "next_id")
    spawned = {c["field"]: c["value"] for c in changes if c["entity_id"] == next_id}
    assert spawned["title"] == "Lab report"
    assert spawned["number"] == 2


def test_due_range_filter(client, home):
    for title, due in [("Oct", "2026-10-15"), ("Nov", "2026-11-10"), ("Undated", None)]:
        client.post("/items", json={"project": "HOME", "title": title, "due": due})
    titles = [i["title"] for i in client.get("/items", params={"due_from": "2026-11-01", "due_to": "2026-11-30"}).json()]
    assert titles == ["Nov"]
