import random

import pytest

from bca.meals import MealProblem


def fixture():
    catalog = []
    for category, cost, energy, protein, fiber, quantity, unit in [
        ("staple", 2000, 200, 4, 1, 100, "g"),
        ("protein", 4000, 200, 16, 0, 60, "g"),
        ("vegetable", 2000, 50, 2, 4, 80, "g"),
        ("fruit", 1000, 50, 0, 2, 1, "piece"),
    ]:
        catalog.append(
            {
                "id": category,
                "name": category.title(),
                "category": category,
                "cost": cost,
                "energy": energy,
                "protein": protein,
                "fiber": fiber,
                "tags": [],
                "ingredients": [
                    {
                        "id": "shared",
                        "name": "Shared",
                        "quantity": quantity,
                        "unit": unit,
                    }
                ],
                "batch_size": 50,
                "work_minutes": 10,
            }
        )
    planning = {
        "servings": [51, 50, 50, 50, 50],
        "budget_per_serving": 10000,
        "energy_min": 500,
        "energy_max": 750,
        "protein_min": 20,
        "fiber_min": 6,
        "kitchen_capacity": 100,
        "max_protein_repeats": 5,
        "max_menu_repeats": 5,
        "exclusions": [],
        "weights": {
            "cost": 1,
            "budget": 5,
            "nutrition": 8,
            "variety": 2,
            "workload": 3,
        },
    }
    return catalog, planning, ["staple", "protein", "vegetable", "fruit"] * 5


def test_evaluation_scales_school_quantities_and_preserves_ingredient_units():
    catalog, planning, schedule = fixture()
    result = MealProblem(catalog, planning).evaluate(schedule)
    assert result["totals"]["cost"] == 2259000
    assert result["totals"]["budget"] == 2510000
    assert result["totals"]["servings"] == 251
    assert result["totals"]["workload"] == 240
    assert result["days"][0]["nutrition"] == {"energy": 500, "protein": 22, "fiber": 7}
    assert result["days"][0]["workload"] == 80
    assert result["days"][0]["component_quantities"][0]["batches"] == 2
    assert [(i["unit"], i["quantity"]) for i in result["totals"]["ingredients"]] == [
        ("g", 60240),
        ("piece", 251),
    ]
    assert result["score"] == pytest.approx(0.9)
    assert result["fitness"] == pytest.approx(1 / 1.9)
    assert result["targets_met"] is True


def test_evaluation_reports_each_normalized_target_violation_and_weighted_score():
    catalog, planning, schedule = fixture()
    catalog[0]["energy"] = 100
    catalog[3]["cost"] = 3000
    planning.update(kitchen_capacity=20, max_protein_repeats=2, max_menu_repeats=1)
    result = MealProblem(catalog, planning).evaluate(schedule)
    assert result["metrics"] == pytest.approx(
        {"cost": 1.1, "budget": 0.1, "nutrition": 0.2, "variety": 1.4, "workload": 1.4}
    )
    assert result["contributions"] == pytest.approx(
        {"cost": 1.1, "budget": 0.5, "nutrition": 1.6, "variety": 2.8, "workload": 4.2}
    )
    assert result["score"] == pytest.approx(10.2)
    assert result["targets_met"] is False
    assert len(result["days"][0]["violations"]) == 3
    assert any(
        "protein" in message.lower() and "5" in message
        for message in result["violations"]
    )
    assert any("identical menu" in message.lower() for message in result["violations"])


def test_targets_too_small_for_finite_scoring_are_rejected():
    catalog, planning, schedule = fixture()
    planning["budget_per_serving"] = 1e-320
    with pytest.raises(ValueError):
        MealProblem(catalog, planning).evaluate(schedule)


@pytest.mark.parametrize(
    "field,value",
    [
        ("servings", [True, 50, 50, 50, 50]),
        ("servings", [0, 50, 50, 50, 50]),
        ("energy_min", float("nan")),
        ("energy_max", float("inf")),
        ("protein_min", False),
        ("energy_max", 100),
        ("servings", [50] * 4),
    ],
)
def test_invalid_planning_values_are_rejected_at_meal_problem_seam(field, value):
    catalog, planning, schedule = fixture()
    planning[field] = value
    with pytest.raises(ValueError):
        MealProblem(catalog, planning).evaluate(schedule)


@pytest.mark.parametrize(
    "field,value",
    [
        ("cost", True),
        ("fiber", -1),
        ("work_minutes", float("inf")),
        ("batch_size", 0),
        ("batch_size", 1.5),
        ("name", "   "),
    ],
)
def test_invalid_components_are_rejected_at_meal_problem_seam(field, value):
    catalog, planning, schedule = fixture()
    catalog[0][field] = value
    with pytest.raises(ValueError):
        MealProblem(catalog, planning).evaluate(schedule)


def test_excluded_categories_and_duplicate_ids_are_explained():
    catalog, planning, _schedule = fixture()
    catalog[1]["tags"] = ["egg"]
    planning["exclusions"] = ["egg"]
    with pytest.raises(ValueError, match="No eligible components for: protein"):
        MealProblem(catalog, planning)
    planning["exclusions"] = []
    catalog[1]["id"] = "staple"
    with pytest.raises(ValueError, match="unique"):
        MealProblem(catalog, planning)


def test_sample_and_neighbor_preserve_validity_and_snapshot_inputs():
    from copy import deepcopy

    catalog, planning, schedule = fixture()
    extra = deepcopy(catalog[1])
    extra.update(id="other-protein", name="Other protein", tags=["excluded"])
    catalog.append(extra)
    allowed = deepcopy(extra)
    allowed.update(id="allowed-protein", tags=[])
    catalog.append(allowed)
    planning["exclusions"] = ["excluded"]
    problem = MealProblem(catalog, planning)
    catalog[0]["cost"] = 999999
    planning["servings"][0] = 999999
    assert problem.evaluate(schedule)["totals"]["cost"] == 2259000
    rng = random.Random(42)
    for _ in range(30):
        sampled = problem.sample(rng)
        candidate = problem.neighbor(schedule, sampled, rng)
        assert "other-protein" not in sampled
        assert sum(a != b for a, b in zip(schedule, candidate)) == 1
        problem.evaluate(candidate)
    assert (
        problem.neighbor(schedule, schedule, random.Random(1)).count("allowed-protein")
        == 1
    )


def test_large_catalog_and_single_option_categories_remain_evaluable():
    from copy import deepcopy

    catalog, planning, schedule = fixture()
    assert (
        MealProblem(catalog, planning).neighbor(schedule, schedule, random.Random(1))
        == schedule
    )
    originals = deepcopy(catalog)
    for index in range(996):
        component = deepcopy(originals[index % 4])
        component["id"] += "-" + str(index)
        catalog.append(component)
    problem = MealProblem(catalog, planning)
    result = problem.evaluate(problem.sample(random.Random(7)))
    assert result["totals"]["cost"] == 2259000


@pytest.mark.parametrize(
    "schedule", [[], ["staple"] * 20, ["missing"] * 20, [False] * 20]
)
def test_malformed_or_wrong_category_schedules_are_rejected(schedule):
    catalog, planning, _ = fixture()
    with pytest.raises(ValueError):
        MealProblem(catalog, planning).evaluate(schedule)


def test_nutrition_measures_excess_energy_and_independent_shortfalls_per_serving():
    catalog, planning, schedule = fixture()
    planning.update(energy_max=400, energy_min=300, protein_min=44, fiber_min=14)
    result = MealProblem(catalog, planning).evaluate(schedule)
    assert result["metrics"]["nutrition"] == pytest.approx(1.25)
    assert len(result["days"][0]["violations"]) == 3


def test_demonstration_catalog_exposes_tradeoffs_and_keeps_a_feasible_week():
    from bca.catalog import default_configuration

    config = default_configuration()
    problem = MealProblem(config["catalog"], config["planning"])
    feasible = [
        "rice",
        "chicken",
        "spinach",
        "papaya",
        "brown-rice",
        "egg",
        "carrot",
        "banana",
        "corn",
        "tempeh",
        "cabbage",
        "orange",
        "potato",
        "tofu",
        "long-beans",
        "watermelon",
        "rice",
        "fish",
        "mixed-vegetables",
        "guava",
    ]
    result = problem.evaluate(feasible)
    assert result["targets_met"] is True
    assert result["totals"]["cost"] == 18950000
    assert result["totals"]["workload"] == 1500
    candidate = feasible.copy()
    candidate[1] = "protein-light-demo"
    candidate[5] = "protein-feast-demo"
    result = problem.evaluate(candidate)
    # Monday: 260+40+70+90 kcal; 5+2+3+1 g protein. Tuesday's
    # Rp2200+12000+1300+1500 menu has 20 protein batches at 40 min.
    assert result["days"][0]["nutrition"] == {"energy": 460, "protein": 11, "fiber": 8}
    assert result["days"][0]["cost"] == 2400000
    assert result["days"][1]["cost"] == 8500000
    assert result["days"][1]["workload"] == 975
    assert result["metrics"] == pytest.approx(
        {
            "cost": 0.874,
            "budget": 0.14,
            "nutrition": 0.106,
            "variety": 0,
            "workload": 0.125,
        }
    )
    assert result["score"] == pytest.approx(2.797)
    assert result["targets_met"] is False
    assert len(result["violations"]) == 4
