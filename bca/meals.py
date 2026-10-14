"""The public meal problem seam, independent of optimizer and browser timing."""

from collections import defaultdict
from math import ceil
from random import Random

from .models import CATEGORIES, DAYS, Component, Planning


def _ingredients(rows):
    totals = {}
    for row in rows:
        key = (row["id"], row["unit"])
        if key not in totals:
            totals[key] = dict(row, quantity=0.0)
        totals[key]["quantity"] += row["quantity"]
    return [totals[key] for key in sorted(totals)]


class MealProblem:
    """Validate and snapshot a catalog/planning dict or Pydantic model.

    Schedules are 20 component IDs, ordered by weekday then category.
    """

    def __init__(self, catalog, planning):
        if not isinstance(catalog, (list, tuple)) or not 4 <= len(catalog) <= 1000:
            raise ValueError("Catalog must contain between 4 and 1000 components")
        self.catalog = tuple(
            Component.model_validate(
                item.model_dump() if isinstance(item, Component) else item
            )
            for item in catalog
        )
        self.planning = Planning.model_validate(
            planning.model_dump() if isinstance(planning, Planning) else planning
        )
        self.components = {item.id: item for item in self.catalog}
        if len(self.components) != len(self.catalog):
            raise ValueError("Component IDs must be unique")
        excluded = set(self.planning.exclusions)
        self.eligible = {
            category: tuple(
                item.id
                for item in self.catalog
                if item.category == category and not excluded.intersection(item.tags)
            )
            for category in CATEGORIES
        }
        missing = [
            category for category, choices in self.eligible.items() if not choices
        ]
        if missing:
            raise ValueError("No eligible components for: " + ", ".join(missing))

    def _validate_schedule(self, schedule):
        if not isinstance(schedule, (list, tuple)) or len(schedule) != 20:
            raise ValueError("A schedule must contain exactly 20 component IDs")
        for position, component_id in enumerate(schedule):
            category = CATEGORIES[position % 4]
            if (
                not isinstance(component_id, str)
                or component_id not in self.eligible[category]
            ):
                raise ValueError(
                    f"Invalid or excluded {category} at position {position}"
                )
        return tuple(schedule)

    def sample(self, rng: Random):
        return [
            rng.choice(self.eligible[category]) for _ in DAYS for category in CATEGORIES
        ]

    def neighbor(self, schedule, partner, rng: Random):
        schedule = self._validate_schedule(schedule)
        partner = self._validate_schedule(partner)
        movable = [
            index
            for index in range(20)
            if len(self.eligible[CATEGORIES[index % 4]]) > 1
        ]
        if not movable:
            return list(schedule)
        differences = [index for index in movable if schedule[index] != partner[index]]
        position = rng.choice(differences or movable)
        candidate = list(schedule)
        if partner[position] != schedule[position]:
            candidate[position] = partner[position]
        else:
            alternatives = [
                choice
                for choice in self.eligible[CATEGORIES[position % 4]]
                if choice != schedule[position]
            ]
            candidate[position] = rng.choice(alternatives)
        return candidate

    def evaluate(self, schedule):
        schedule = self._validate_schedule(schedule)
        days = []
        for index, day in enumerate(DAYS):
            components = [
                self.components[key] for key in schedule[index * 4 : index * 4 + 4]
            ]
            servings = self.planning.servings[index]
            nutrition = {
                metric: sum(getattr(component, metric) for component in components)
                for metric in ("energy", "protein", "fiber")
            }
            cost_per_serving = sum(component.cost for component in components)
            quantities = [
                {
                    "id": item.id,
                    "name": item.name,
                    "servings": servings,
                    "batches": ceil(servings / item.batch_size),
                }
                for item in components
            ]
            workload = sum(
                quantity["batches"] * item.work_minutes
                for quantity, item in zip(quantities, components)
            )
            ingredients = _ingredients(
                [
                    dict(
                        ingredient.model_dump(), quantity=ingredient.quantity * servings
                    )
                    for component in components
                    for ingredient in component.ingredients
                ]
            )
            days.append(
                {
                    "day": day,
                    "servings": servings,
                    "components": [item.model_dump() for item in components],
                    "nutrition": nutrition,
                    "cost_per_serving": cost_per_serving,
                    "cost": cost_per_serving * servings,
                    "budget": self.planning.budget_per_serving * servings,
                    "workload": workload,
                    "component_quantities": quantities,
                    "ingredients": ingredients,
                    "violations": [],
                }
            )
        totals = {
            metric: sum(day[metric] for day in days)
            for metric in ("cost", "budget", "servings", "workload")
        }
        totals["ingredients"] = _ingredients(
            [row for day in days for row in day["ingredients"]]
        )
        violations = []
        budget_penalties, nutrition_penalties, workload_penalties = [], [], []
        for day in days:
            messages = day["violations"]
            budget_excess = max(0.0, (day["cost"] - day["budget"]) / day["budget"])
            workload_excess = max(
                0.0,
                (day["workload"] - self.planning.kitchen_capacity)
                / self.planning.kitchen_capacity,
            )
            nutrition = day["nutrition"]
            energy = nutrition["energy"]
            energy_penalty = max(
                0.0, (self.planning.energy_min - energy) / self.planning.energy_min
            )
            energy_penalty += max(
                0.0, (energy - self.planning.energy_max) / self.planning.energy_max
            )
            protein_penalty = max(
                0.0,
                (self.planning.protein_min - nutrition["protein"])
                / self.planning.protein_min,
            )
            fiber_penalty = max(
                0.0,
                (self.planning.fiber_min - nutrition["fiber"])
                / self.planning.fiber_min,
            )
            if budget_excess > 0:
                messages.append(
                    f"{day['day']}: cost exceeds budget by Rp{day['cost'] - day['budget']:,.0f}"
                )
            if energy_penalty > 0:
                messages.append(
                    f"{day['day']}: energy {energy:g} kcal is outside "
                    f"{self.planning.energy_min:g}-{self.planning.energy_max:g} kcal"
                )
            if protein_penalty > 0:
                messages.append(
                    f"{day['day']}: protein {nutrition['protein']:g} g is below "
                    f"{self.planning.protein_min:g} g"
                )
            if fiber_penalty > 0:
                messages.append(
                    f"{day['day']}: fiber {nutrition['fiber']:g} g is below "
                    f"{self.planning.fiber_min:g} g"
                )
            if workload_excess > 0:
                messages.append(
                    f"{day['day']}: kitchen workload exceeds capacity by "
                    f"{day['workload'] - self.planning.kitchen_capacity:g} person-minutes"
                )
            budget_penalties.append(budget_excess)
            nutrition_penalties.append(energy_penalty + protein_penalty + fiber_penalty)
            workload_penalties.append(workload_excess)
            violations.extend(messages)
        protein_counts, menu_counts = defaultdict(int), defaultdict(int)
        for index in range(5):
            protein_counts[schedule[index * 4 + 1]] += 1
            menu_counts[schedule[index * 4 : index * 4 + 4]] += 1
        repeat_excess = 0
        for component_id, count in protein_counts.items():
            excess = max(0, count - self.planning.max_protein_repeats)
            repeat_excess += excess
            if excess:
                violations.append(
                    f"Protein {self.components[component_id].name} appears {count} times; "
                    f"limit is {self.planning.max_protein_repeats}"
                )
        for menu, count in menu_counts.items():
            excess = max(0, count - self.planning.max_menu_repeats)
            repeat_excess += excess
            if excess:
                label = ", ".join(self.components[key].name for key in menu)
                violations.append(
                    f"Identical menu ({label}) appears {count} times; "
                    f"limit is {self.planning.max_menu_repeats}"
                )
        metrics = {
            "cost": totals["cost"] / totals["budget"],
            "budget": sum(budget_penalties) / 5,
            "nutrition": sum(nutrition_penalties) / 5,
            "variety": repeat_excess / 5,
            "workload": sum(workload_penalties) / 5,
        }
        contributions = {
            key: value * getattr(self.planning.weights, key)
            for key, value in metrics.items()
        }
        score = sum(contributions.values())
        return {
            "score": score,
            "fitness": 1 / (1 + score),
            "contributions": contributions,
            "metrics": metrics,
            "days": days,
            "totals": totals,
            "violations": violations,
            "targets_met": not violations,
        }
