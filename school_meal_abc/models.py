"""Validated, bounded transport models; catalog values describe one serving."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

CATEGORIES = ("staple", "protein", "vegetable", "fruit")
DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")
Category = Literal["staple", "protein", "vegetable", "fruit"]
Text = Annotated[str, Field(strict=True, min_length=1, max_length=160)]
Number = Annotated[float, Field(strict=True, ge=0, le=10_000_000, allow_inf_nan=False)]
Positive = Annotated[
    float, Field(strict=True, ge=0.001, le=10_000_000, allow_inf_nan=False)
]
Count = Annotated[int, Field(strict=True, ge=1, le=1_000_000)]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Ingredient(Model):
    id: Text
    name: Text
    quantity: Number
    unit: Text


class Component(Model):
    id: Text
    name: Text
    category: Category
    cost: Number
    energy: Number
    protein: Number
    fiber: Number
    tags: list[Text] = Field(default_factory=list, max_length=100)
    ingredients: list[Ingredient] = Field(default_factory=list, max_length=100)
    batch_size: Count
    work_minutes: Number


class Weights(Model):
    cost: Number = 1
    budget: Number = 5
    nutrition: Number = 8
    variety: Number = 2
    workload: Number = 3


class Planning(Model):
    servings: list[Count] = Field(min_length=5, max_length=5)
    budget_per_serving: Positive
    energy_min: Positive
    energy_max: Positive
    protein_min: Positive
    fiber_min: Positive
    kitchen_capacity: Positive
    max_protein_repeats: Annotated[int, Field(strict=True, ge=1, le=5)]
    max_menu_repeats: Annotated[int, Field(strict=True, ge=1, le=5)]
    exclusions: list[Text] = Field(default_factory=list, max_length=100)
    weights: Weights = Field(default_factory=Weights)

    @model_validator(mode="after")
    def check_energy_range(self):
        if self.energy_max < self.energy_min:
            raise ValueError("energy_max must be at least energy_min")
        return self


class Algorithm(Model):
    sources: Annotated[int, Field(strict=True, ge=2, le=80)] = 16
    onlookers: Annotated[int, Field(strict=True, ge=1, le=160)] = 16
    limit: Annotated[int, Field(strict=True, ge=1, le=10000)] = 40
    max_cycles: Annotated[int, Field(strict=True, ge=1, le=2000)] = 100
    patience: Annotated[int, Field(strict=True, ge=0, le=2000)] = 20
    seed: Annotated[int, Field(strict=True, ge=-(2**63), le=2**63 - 1)] = 42


class Configuration(Model):
    catalog: list[Component] = Field(min_length=4, max_length=1000)
    planning: Planning
    algorithm: Algorithm = Field(default_factory=Algorithm)


class EvaluateRequest(Model):
    catalog: list[Component] = Field(min_length=4, max_length=1000)
    planning: Planning
    schedule: list[Text] = Field(min_length=20, max_length=20)
