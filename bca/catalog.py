"""Editable Indonesian-style demonstration data, not official nutrition standards."""

from copy import deepcopy

from .models import CATEGORIES, DAYS, Algorithm, Planning

# Each tuple: id, label, rupiah, kcal, protein g, fiber g, ingredient grams.
_STAPLES = [
    ("rice", "Nasi putih", 1800, 260, 5, 1, 75),
    ("brown-rice", "Nasi merah", 2200, 250, 5, 3, 75),
    ("corn", "Nasi jagung", 1700, 240, 5, 3, 85),
    ("potato", "Kentang kukus", 1900, 230, 5, 3, 250),
]
_PROTEINS = [
    ("chicken", "Ayam panggang", 4000, 190, 25, 0, 90),
    ("egg", "Telur balado", 2800, 180, 14, 0, 100),
    ("tempeh", "Tempe orek", 2200, 190, 17, 5, 90),
    ("tofu", "Tahu bumbu kuning", 2000, 160, 14, 2, 120),
    ("fish", "Ikan kembung panggang", 3800, 190, 23, 0, 100),
]
_VEGETABLES = [
    ("spinach", "Sayur bayam", 1200, 70, 3, 4, 100),
    ("carrot", "Wortel tumis", 1300, 80, 2, 4, 100),
    ("cabbage", "Tumis kol", 1100, 70, 2, 4, 100),
    ("long-beans", "Tumis kacang panjang", 1400, 90, 3, 5, 100),
    ("mixed-vegetables", "Capcay", 1700, 100, 3, 4, 120),
]
_FRUIT = [
    ("papaya", "Pepaya", 1200, 90, 1, 3, 150),
    ("banana", "Pisang", 1500, 110, 1, 3, 120),
    ("orange", "Jeruk", 1700, 80, 1, 3, 160),
    ("watermelon", "Semangka", 1000, 80, 1, 2, 200),
    ("guava", "Jambu biji", 1600, 100, 2, 5, 150),
]


def default_configuration():
    """Return a new JSON-ready catalog and confirmed editable demonstration defaults."""
    catalog = []
    for category, rows, work in [
        ("staple", _STAPLES, 10),
        ("protein", _PROTEINS, 25),
        ("vegetable", _VEGETABLES, 20),
        ("fruit", _FRUIT, 5),
    ]:
        for key, name, cost, energy, protein, fiber, grams in rows:
            tags = []
            if key in ("tempeh", "tofu"):
                tags.append("soy")
            if key == "egg":
                tags.append("egg")
            if key == "fish":
                tags.append("fish")
            catalog.append(
                {
                    "id": key,
                    "name": name,
                    "category": category,
                    "cost": cost,
                    "energy": energy,
                    "protein": protein,
                    "fiber": fiber,
                    "tags": tags,
                    "ingredients": [
                        {
                            "id": key + "-raw",
                            "name": name + " (bahan)",
                            "quantity": grams,
                            "unit": "g",
                        }
                    ],
                    "batch_size": 100,
                    "work_minutes": work,
                }
            )
    planning = Planning(
        servings=[500] * 5,
        budget_per_serving=10000,
        energy_min=500,
        energy_max=750,
        protein_min=20,
        fiber_min=6,
        kitchen_capacity=600,
        max_protein_repeats=2,
        max_menu_repeats=1,
        exclusions=[],
    )
    return deepcopy(
        {
            "catalog": catalog,
            "planning": planning.model_dump(),
            "algorithm": Algorithm().model_dump(),
            "categories": list(CATEGORIES),
            "days": list(DAYS),
        }
    )
