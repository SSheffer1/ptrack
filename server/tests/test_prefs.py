from test_sync import change, sync


def test_set_and_reset_preferences(client):
    assert client.get("/me/prefs").json() == {}
    r = client.patch("/me/prefs", json={"week_start": "monday", "untimed_hour": 8, "reminders_timed": ["-1D", "-8h"]})
    assert r.json() == {"week_start": "monday", "untimed_hour": 8, "reminders_timed": ["-1d", "-8h"]}
    assert client.patch("/me/prefs", json={"week_start": None}).json() == {"untimed_hour": 8, "reminders_timed": ["-1d", "-8h"]}


def test_bad_preferences_are_rejected(client):
    for body in [{"week_start": "friday"}, {"untimed_hour": 25}, {"soon_days": -1}, {"nonsense": 1},
                 {"reminders_untimed": ["soon"]}, {"default_statuses": ["nope"]}]:
        assert client.patch("/me/prefs", json=body).status_code == 400, body


def test_preferences_sync_only_to_their_owner(client, bob):
    client.patch("/me/prefs", json={"soon_days": 5})
    mine = sync(client, "alice-phone")["changes"]
    assert [(c["entity"], c["field"], c["value"]) for c in mine] == [("prefs", "soon_days", 5)]
    assert sync(bob, "bob-phone")["changes"] == []


def test_cannot_change_someone_elses_preferences(client, bob):
    result = sync(bob, "bob-phone", [change(client.user_id, "week_start", "monday", 1000, "prefs")])
    assert [d["reason"] for d in result["dropped"]] == ["you can only change your own preferences"]
    assert client.get("/me/prefs").json() == {}


def test_phone_sets_its_own_preferences(client):
    sync(client, "alice-phone", [change(client.user_id, "default_sort", "due", 1000, "prefs")])
    assert client.get("/me/prefs").json() == {"default_sort": "due"}
