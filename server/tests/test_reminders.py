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
