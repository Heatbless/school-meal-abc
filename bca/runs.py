"""Bounded, process-local live runs. Each operation returns independent data."""

from threading import RLock
from time import monotonic
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Response
from pydantic import Field

from .meals import MealProblem
from .models import Configuration, Model
from .optimizer import BeeColony

router = APIRouter(prefix="/api/runs")
MAX_RUNS = 32
IDLE_SECONDS = 3600
_runs = {}
_lock = RLock()


class StepRequest(Model):
    steps: Annotated[int, Field(strict=True, ge=1, le=100)] = 1


def _expire():
    now = monotonic()
    for key in [
        key for key, (_, touched) in _runs.items() if now - touched > IDLE_SECONDS
    ]:
        del _runs[key]


def _get(run_id):
    _expire()
    if run_id not in _runs:
        raise HTTPException(404, "Run not found or expired. Start a new run.")
    colony, _ = _runs[run_id]
    _runs[run_id] = (colony, monotonic())
    return colony


@router.post("")
def create_run(configuration: Configuration):
    try:
        colony = BeeColony(
            MealProblem(configuration.catalog, configuration.planning),
            configuration.algorithm,
        )
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    with _lock:
        _expire()
        if len(_runs) >= MAX_RUNS:
            raise HTTPException(
                503,
                "Host run capacity reached. Reset or delete an existing run and retry.",
            )
        run_id = uuid4().hex
        _runs[run_id] = (colony, monotonic())
        return {"id": run_id, "state": colony.snapshot()}


@router.get("/{run_id}")
def get_run(run_id: str):
    with _lock:
        return _get(run_id).snapshot()


@router.post("/{run_id}/step")
def step_run(run_id: str, request: StepRequest):
    with _lock:
        colony = _get(run_id)
        events = colony.advance(request.steps)
        return {"events": events, "state": colony.snapshot()}


@router.post("/{run_id}/stop")
def stop_run(run_id: str):
    with _lock:
        return _get(run_id).stop()


@router.delete("/{run_id}", status_code=204)
def delete_run(run_id: str):
    with _lock:
        _get(run_id)
        del _runs[run_id]
        return Response(status_code=204)
