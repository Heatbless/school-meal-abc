"""Exercise downloaded result documents from real HTTP evaluation output."""

import csv
import io
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from test_meals import fixture

from bca.app import app


def exported(format):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is needed to exercise the browser export public interface")
    catalog, planning, schedule = fixture()
    catalog[0]["name"] = '=SUM(1,2)\n"Rice"'
    with TestClient(app) as client:
        evaluation = client.post(
            "/api/evaluate",
            json={"catalog": catalog, "planning": planning, "schedule": schedule},
        ).json()
    configuration = {
        "catalog": catalog,
        "planning": planning,
        "algorithm": {"seed": 42, "sources": 16},
    }
    script = """
import fs from 'node:fs';
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const source = fs.readFileSync(input.module, 'utf8');
const {exportResults} = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
process.stdout.write(JSON.stringify(exportResults(input.best, input.configuration, input.format)));
"""
    result = subprocess.run(
        [node, "--input-type=module", "-e", script],
        input=json.dumps(
            {
                "module": str(Path(__file__).parents[1] / "bca/static/results.js"),
                "best": {"schedule": schedule, "evaluation": evaluation},
                "configuration": configuration,
                "format": format,
            }
        ),
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)


def test_json_download_preserves_host_result_and_reproducible_configuration():
    download = exported("json")
    result = json.loads(download["content"])
    assert result["configuration"]["algorithm"]["seed"] == 42
    assert result["configuration"]["catalog"][0]["name"] == '=SUM(1,2)\n"Rice"'
    assert result["best"]["evaluation"]["totals"]["cost"] == 2259000
    assert result["best"]["evaluation"]["totals"]["ingredients"] == [
        {"id": "shared", "name": "Shared", "quantity": 60240, "unit": "g"},
        {"id": "shared", "name": "Shared", "quantity": 251, "unit": "piece"},
    ]
    assert download["filename"].endswith(".json")


def test_csv_download_contains_menus_procurement_units_and_replay_settings():
    download = exported("csv")
    rows = list(csv.DictReader(io.StringIO(download["content"])))
    purchases = [row for row in rows if row["section"] == "purchasing"]
    assert [(row["value"], row["unit"]) for row in purchases] == [
        ("60240", "g"),
        ("251", "piece"),
    ]
    monday = [
        row for row in rows if row["section"] == "component" and row["day"] == "Monday"
    ]
    assert len(monday) == 4
    assert monday[0]["name"] == '\'=SUM(1,2)\n"Rice"'
    assert json.loads(monday[0]["details"])["batches"] == 2
    assert monday[0]["value"] == "51"
    configuration = json.loads(
        next(row["details"] for row in rows if row["section"] == "configuration")
    )
    assert configuration["algorithm"]["seed"] == 42
    assert configuration["planning"]["servings"] == [51, 50, 50, 50, 50]
    assert any(row["id"] == "cost" and row["value"] == "2259000" for row in rows)
