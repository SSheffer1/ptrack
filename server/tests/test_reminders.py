import pytest

from ptrack.reminders import normalize_reminders


def test_normalize_sorts_dedupes_and_lowercases():
    assert normalize_reminders([" -8H", "0", "-1d", "-8h"]) == ["-1d", "-8h", "0"]
    assert normalize_reminders(None) is None
    assert normalize_reminders([]) == []


@pytest.mark.parametrize("bad", ["8h", "-1w", "-h", "soon", "+1d", "-12345m"])
def test_rejects_bad_offsets(bad):
    with pytest.raises(ValueError):
        normalize_reminders([bad])


def test_api_default_explicit_and_none(client, home):
    item = client.post("/items", json={"project": "HOME", "title": "Exam", "due": "2026-10-28"}).json()
    assert item["reminders"] is None  # default
    item = client.patch("/items/HOME-1", json={"reminders": ["-1d", "-8h"]}).json()
    assert item["reminders"] == ["-1d", "-8h"]
    item = client.patch("/items/HOME-1", json={"reminders": []}).json()
    assert item["reminders"] == []
    item = client.patch("/items/HOME-1", json={"reminders": None}).json()
    assert item["reminders"] is None
    assert client.patch("/items/HOME-1", json={"reminders": ["tomorrow"]}).status_code == 400


def test_specific_times():
    assert normalize_reminders(["@2026-10-27t19:30", "-8h", "@2026-10-26T09:00"]) == [
        "-8h", "@2026-10-26T09:00", "@2026-10-27T19:30"]
    for bad in ["@2026-13-01T10:00", "@2026-10-27 19:30", "@tomorrow"]:
        with pytest.raises(ValueError):
            normalize_reminders([bad])
    with pytest.raises(ValueError):
        normalize_reminders(["@2026-10-27T19:30"], allow_specific_times=False)


def test_shift_specific_times():
    from ptrack.reminders import shift_reminders
    assert shift_reminders(["-1d", "@2026-10-28T19:30"], 7) == ["-1d", "@2026-11-04T19:30"]
    assert shift_reminders(None, 7) is None


def test_recurring_copy_moves_specific_time_reminders(client, home):
    from datetime import date, timedelta
    due = date.today() + timedelta(days=3)
    at = f"@{(due - timedelta(days=1)).isoformat()}T19:30"
    client.post("/items", json={"project": "HOME", "title": "Lab", "due": due.isoformat(),
                                "repeat": "FREQ=WEEKLY", "reminders": ["-8h", at]})
    done = client.patch("/items/HOME-1", json={"status": "done"}).json()
    nxt = client.get(f"/items/{done['next_id']}").json()
    assert nxt["reminders"] == ["-8h", f"@{(due + timedelta(days=6)).isoformat()}T19:30"]


def test_preferences_reject_specific_times(client):
    assert client.patch("/me/prefs", json={"reminders": ["@2026-10-27T19:30"]}).status_code == 400
