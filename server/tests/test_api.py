def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_project_keys_are_unique(client, home):
    r = client.post("/projects", json={"key": "HOME", "name": "Again"})
    assert r.status_code == 409


def test_project_key_format(client):
    r = client.post("/projects", json={"key": "home", "name": "Lowercase"})
    assert r.status_code == 422


def test_tickets_get_sequential_keys(client, home):
    a = client.post("/items", json={"project": "HOME", "title": "Fix bike"}).json()
    b = client.post("/items", json={"project": "HOME", "title": "Clean gutters"}).json()
    assert (a["key"], b["key"]) == ("HOME-1", "HOME-2")
    assert a["status"] == "todo"


def test_get_by_key_or_id(client, home):
    created = client.post("/items", json={"project": "HOME", "title": "Fix bike"}).json()
    assert client.get("/items/HOME-1").json()["id"] == created["id"]
    assert client.get(f"/items/{created['id']}").json()["key"] == "HOME-1"
    assert client.get("/items/HOME-99").status_code == 404


def test_update_and_history(client, home):
    client.post("/items", json={"project": "HOME", "title": "Fix bike"})
    r = client.patch("/items/HOME-1", json={"status": "in_progress", "priority": "high"})
    assert r.json()["status"] == "in_progress"
    client.patch("/items/HOME-1", json={"status": "done"})

    statuses = [c["value"] for c in client.get("/items/HOME-1/history").json() if c["field"] == "status"]
    assert statuses == ["todo", "in_progress", "done"]


def test_invalid_update_is_rejected(client, home):
    client.post("/items", json={"project": "HOME", "title": "Fix bike"})
    assert client.patch("/items/HOME-1", json={"status": "nope"}).status_code == 422
    assert client.patch("/items/HOME-1", json={"title": None}).status_code == 400


def test_clear_due_date(client, home):
    client.post("/items", json={"project": "HOME", "title": "Taxes", "due": "2027-04-15"})
    assert client.patch("/items/HOME-1", json={"due": None}).json()["due"] is None


def test_delete_hides_item(client, home):
    client.post("/items", json={"project": "HOME", "title": "Fix bike"})
    assert client.delete("/items/HOME-1").status_code == 204
    assert client.get("/items/HOME-1").status_code == 404
    assert client.get("/items").json() == []


def test_list_filters(client, home):
    client.post("/projects", json={"key": "CAR", "name": "Car"})
    client.post("/items", json={"project": "HOME", "title": "Fix sink", "labels": ["plumbing"]})
    client.post("/items", json={"project": "HOME", "title": "Paint fence", "status": "backlog"})
    client.post("/items", json={"project": "CAR", "title": "Oil change"})

    def keys(**params):
        return [i["key"] for i in client.get("/items", params=params).json()]

    assert keys(project="CAR") == ["CAR-1"]
    assert keys(project=["CAR", "HOME"]) == ["HOME-1", "HOME-2", "CAR-1"]  # several projects
    assert keys(status=["todo"]) == ["HOME-1", "CAR-1"]
    assert keys(status=["todo", "backlog"], project="HOME") == ["HOME-1", "HOME-2"]
    assert keys(label="plumbing") == ["HOME-1"]
    assert keys(q="fence") == ["HOME-2"]


def test_comments(client, home):
    client.post("/items", json={"project": "HOME", "title": "Fix bike"})
    client.post("/items/HOME-1/comments", json={"body": "Need a new chain"})
    comments = client.get("/items/HOME-1/comments").json()
    assert [c["body"] for c in comments] == ["Need a new chain"]
