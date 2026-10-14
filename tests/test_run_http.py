from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from school_meal_abc.app import app
from school_meal_abc.catalog import default_configuration


def test_runs_are_isolated_and_reading_does_not_advance():
    client = TestClient(app)
    config = default_configuration()
    first = client.post(
        "/api/runs", json={k: config[k] for k in ("catalog", "planning", "algorithm")}
    )
    assert first.status_code == 200
    first = first.json()
    second = client.post(
        "/api/runs", json={k: config[k] for k in ("catalog", "planning", "algorithm")}
    ).json()
    assert first["id"] != second["id"]
    assert client.get(f"/api/runs/{first['id']}").json() == first["state"]
    stepped = client.post(f"/api/runs/{first['id']}/step", json={"steps": 1}).json()
    assert stepped["events"][0]["type"] == "initialized"
    assert stepped["state"]["sequence"] == 1
    assert client.get(f"/api/runs/{second['id']}").json()["sequence"] == 0
    stopped = client.post(f"/api/runs/{first['id']}/stop").json()
    assert stopped["status"] == "stopped"
    assert (
        client.post(f"/api/runs/{first['id']}/step", json={"steps": 2}).json()["events"]
        == []
    )
    assert client.delete(f"/api/runs/{first['id']}").status_code == 204
    assert client.get(f"/api/runs/{first['id']}").status_code == 404
    client.delete(f"/api/runs/{second['id']}")


def test_control_validation_and_concurrent_advancement_are_atomic():
    client = TestClient(app)
    config = default_configuration()
    payload = {key: config[key] for key in ("catalog", "planning", "algorithm")}
    run = client.post("/api/runs", json=payload).json()
    path = f"/api/runs/{run['id']}"
    try:
        for invalid in (0, 101, True, 1.5, "1"):
            assert (
                client.post(path + "/step", json={"steps": invalid}).status_code == 422
            )
        assert client.get(path).json()["evaluations"] == 0
        with ThreadPoolExecutor(max_workers=4) as pool:
            responses = list(
                pool.map(
                    lambda _: client.post(path + "/step", json={"steps": 1}).json(),
                    range(8),
                )
            )
        assert sorted(result["events"][0]["seq"] for result in responses) == list(
            range(1, 9)
        )
        assert client.get(path).json()["sequence"] == 8
        payload["planning"]["exclusions"] = list(
            {
                tag
                for item in config["catalog"]
                if item["category"] == "protein"
                for tag in item["tags"]
            }
        )
        payload["catalog"] = [
            item for item in payload["catalog"] if item["category"] != "protein"
        ]
        assert client.post("/api/runs", json=payload).status_code == 422
    finally:
        client.delete(path)


def test_host_run_storage_is_bounded_and_deletion_frees_capacity():
    client = TestClient(app)
    config = default_configuration()
    payload = {key: config[key] for key in ("catalog", "planning", "algorithm")}
    ids = []
    try:
        for _ in range(32):
            response = client.post("/api/runs", json=payload)
            assert response.status_code == 200
            ids.append(response.json()["id"])
        assert client.post("/api/runs", json=payload).status_code == 503
        client.delete(f"/api/runs/{ids.pop()}")
        response = client.post("/api/runs", json=payload)
        assert response.status_code == 200
        ids.append(response.json()["id"])
    finally:
        for run_id in ids:
            client.delete(f"/api/runs/{run_id}")
