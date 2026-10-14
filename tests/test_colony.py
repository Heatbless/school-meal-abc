from itertools import product

import pytest

from bca.catalog import default_configuration
from bca.meals import MealProblem
from bca.optimizer import BeeColony


def colony(**overrides):
    config = default_configuration()
    config["algorithm"].update(
        sources=3, onlookers=2, max_cycles=2, patience=0, **overrides
    )
    return BeeColony(
        MealProblem(config["catalog"], config["planning"]), config["algorithm"]
    )


def test_initialization_is_an_explicit_advancement_and_seed_replays():
    first, second = colony(), colony()
    assert first.snapshot()["best"] is None
    assert first.snapshot()["evaluations"] == 0
    for _ in range(20):
        assert first.advance() == second.advance()
        assert first.snapshot() == second.snapshot()
    assert first.snapshot()["status"] == "completed"
    assert first.snapshot()["cycle"] == 2
    assert first.advance() == []


def test_greedy_counters_and_onlooker_draw_use_population_before_attempt():
    run = colony()
    run.advance()
    while run.snapshot()["status"] == "running":
        before = run.snapshot()
        event = run.advance()[0]
        after = run.snapshot()
        if event["type"] != "attempt":
            continue
        old = before["sources"][event["source"]]
        current = after["sources"][event["source"]]
        assert event["partner"] != event["source"]
        assert event["accepted"] == (event["candidate_score"] < event["old_score"])
        assert current["trials"] == (0 if event["accepted"] else old["trials"] + 1)
        assert current["score"] <= old["score"]
        if event["role"] == "onlooker":
            assert event["probabilities"] == [
                s["probability"] for s in before["sources"]
            ]
            assert sum(event["probabilities"]) == pytest.approx(1)
            lower = sum(event["probabilities"][: event["source"]])
            assert (
                lower <= event["draw"] < lower + event["probabilities"][event["source"]]
            )


def test_scouts_reset_failure_counts_and_cannot_erase_best_memory():
    config = default_configuration()
    config["planning"]["weights"] = {key: 0 for key in config["planning"]["weights"]}
    config["algorithm"].update(
        sources=2, onlookers=1, limit=1, max_cycles=1, patience=0
    )
    run = BeeColony(
        MealProblem(config["catalog"], config["planning"]), config["algorithm"]
    )
    run.advance()
    initial_best = run.snapshot()["best"]
    events = run.advance(100)
    scouts = [event for event in events if event["type"] == "scout"]
    assert len(scouts) == 2
    assert all(event["abandoned"]["trials"] >= 1 for event in scouts)
    assert all(event["replacement"]["trials"] == 0 for event in scouts)
    assert run.snapshot()["best"] == initial_best
    assert run.snapshot()["evaluations"] == 7  # 2 initial + 3 attempts + 2 scouts


def test_tiny_cost_problem_matches_independent_exhaustive_optimum():
    config = default_configuration()
    catalog = []
    for category in ("staple", "protein", "vegetable", "fruit"):
        items = [item for item in config["catalog"] if item["category"] == category]
        catalog.extend(items[:2] if category == "protein" else items[:1])
    for item in catalog:
        item["cost"] = (
            100
            if item["category"] != "protein"
            else (200 if item == catalog[1] else 600)
        )
    config["planning"]["servings"] = [1] * 5
    config["planning"]["budget_per_serving"] = 1000
    config["planning"]["weights"] = {
        "cost": 1,
        "budget": 0,
        "nutrition": 0,
        "variety": 0,
        "workload": 0,
    }
    proteins = [item for item in catalog if item["category"] == "protein"]
    # Enumerate all 32 weekly assignments independently: only protein varies.
    optimum = min(
        sum(300 + proteins[choice]["cost"] for choice in choices) / 5000
        for choices in product(range(2), repeat=5)
    )
    assert optimum == 0.5
    config["algorithm"].update(
        sources=4, onlookers=4, max_cycles=30, patience=0, seed=42
    )
    problem = MealProblem(catalog, config["planning"])
    run = BeeColony(problem, config["algorithm"])
    while run.snapshot()["status"] not in ("completed", "stopped"):
        run.advance(100)
    state = run.snapshot()
    assert state["best"]["evaluation"]["score"] == optimum
    assert problem.evaluate(state["best"]["schedule"]) == state["best"]["evaluation"]
    assert all(
        a["score"] >= b["score"] for a, b in zip(state["history"], state["history"][1:])
    )


def test_patience_stop_and_independent_snapshots():
    config = default_configuration()
    config["planning"]["weights"] = {key: 0 for key in config["planning"]["weights"]}
    config["algorithm"].update(sources=2, onlookers=1, max_cycles=30, patience=2)
    run = BeeColony(
        MealProblem(config["catalog"], config["planning"]), config["algorithm"]
    )
    run.advance(100)
    assert run.snapshot()["cycle"] == 2
    assert run.snapshot()["stop_reason"] == "patience"
    snapshot = run.snapshot()
    snapshot["sources"][0]["schedule"][0] = "changed"
    snapshot["best"]["evaluation"]["score"] = -1
    assert run.snapshot()["best"]["evaluation"]["score"] == 0
    assert run.snapshot()["sources"][0]["schedule"][0] != "changed"
    pending = colony()
    assert pending.stop()["stop_reason"] == "user"
    assert pending.advance() == []
    assert pending.snapshot()["evaluations"] == 0
