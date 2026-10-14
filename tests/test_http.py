from fastapi.testclient import TestClient

from school_meal_abc.app import app
from school_meal_abc.catalog import default_configuration
from school_meal_abc.meals import MealProblem

client = TestClient(app)


def test_bootstrap_provides_a_usable_demonstration_and_host_evaluates_a_default_feasible_week():
    bootstrap = client.get("/api/bootstrap")
    assert bootstrap.status_code == 200
    config = bootstrap.json()
    assert config["days"] == ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    assert config["categories"] == ["staple", "protein", "vegetable", "fruit"]
    schedule = []
    for protein in ["chicken", "egg", "tempeh", "tofu", "fish"]:
        schedule.extend(["rice", protein, "spinach", "papaya"])
    response = client.post(
        "/api/evaluate",
        json={
            "catalog": config["catalog"],
            "planning": config["planning"],
            "schedule": schedule,
        },
    )
    assert response.status_code == 200
    evaluation = response.json()
    assert evaluation["targets_met"] is True
    assert evaluation["totals"]["servings"] == 2500
    assert evaluation == MealProblem(config["catalog"], config["planning"]).evaluate(
        schedule
    )
    assert client.get("/").status_code == 200


def test_default_configuration_returns_independent_snapshots():
    config = default_configuration()
    config["catalog"][0]["cost"] = 999999
    config["planning"]["servings"][0] = 1
    fresh = default_configuration()
    assert fresh["catalog"][0]["cost"] == 1800
    assert fresh["planning"]["servings"][0] == 500


def test_http_explains_missing_categories_and_invalid_schedule():
    config = default_configuration()
    schedule = ["rice", "chicken", "spinach", "papaya"] * 5
    config["planning"]["exclusions"] = ["soy", "egg", "fish", "all-protein"]
    for component in config["catalog"]:
        if component["category"] == "protein":
            component["tags"].append("all-protein")
    response = client.post(
        "/api/evaluate",
        json={
            "catalog": config["catalog"],
            "planning": config["planning"],
            "schedule": schedule,
        },
    )
    assert response.status_code == 422
    assert "protein" in response.json()["detail"]
    config["planning"]["exclusions"] = []
    schedule[0] = "chicken"
    response = client.post(
        "/api/evaluate",
        json={
            "catalog": config["catalog"],
            "planning": config["planning"],
            "schedule": schedule,
        },
    )
    assert response.status_code == 422


def test_http_handles_nonfinite_raw_json_as_a_readable_validation_error():
    import json

    config = default_configuration()
    config["planning"]["energy_min"] = float("nan")
    body = {
        "catalog": config["catalog"],
        "planning": config["planning"],
        "schedule": ["rice", "chicken", "spinach", "papaya"] * 5,
    }
    response = client.post(
        "/api/evaluate",
        content=json.dumps(body),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert response.json()["detail"]
