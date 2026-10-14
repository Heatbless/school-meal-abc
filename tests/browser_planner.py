"""Optional real-browser planner check: uv run --with playwright python tests/browser_planner.py.

Start the host first; pass --url and --browser to override the Windows defaults.
"""

import argparse
import csv
import io
import json
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8033")
    parser.add_argument(
        "--browser", default="C:/Program Files/Google/Chrome/Application/chrome.exe"
    )
    args = parser.parse_args()
    with sync_playwright() as playwright, tempfile.TemporaryDirectory() as temporary:
        browser = playwright.chromium.launch(
            executable_path=args.browser, headless=True
        )
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        failures = []
        page.on("pageerror", lambda error: failures.append(str(error)))
        page.goto(args.url + "/static/planner.html")
        page.locator("#evaluate-preview").wait_for(state="visible")
        page.wait_for_function("!document.querySelector('#evaluate-preview').disabled")
        page.locator("#servings-0").fill("501")
        page.locator(".catalog-card").first.locator("summary").click()
        page.locator("#component-0-cost").fill("2000")
        malicious = '<img src=x onerror="window.bad=true">'
        page.locator("#component-0-name").fill(malicious)
        page.locator("#add-ingredient-0").click()
        page.locator("#ingredient-0-1-id").fill("salt")
        page.locator("#ingredient-0-1-name").fill("Salt")
        page.locator("#ingredient-0-1-quantity").fill("1")
        page.locator("#ingredient-0-1-unit").fill("g")
        page.locator("#save-configuration").click()
        page.wait_for_function(
            "document.querySelector('#save-status').textContent.includes('Saved')"
        )
        page.reload()
        page.wait_for_function("!document.querySelector('#evaluate-preview').disabled")
        assert page.locator("#servings-0").input_value() == "501"
        page.locator("#evaluate-preview").click()
        page.locator("#preview-results .result-day").first.wait_for()
        assert page.locator("#preview-results .result-day").count() == 5
        assert malicious in page.locator("#preview-results").inner_text()
        assert page.locator("#preview-results img").count() == 0
        assert page.evaluate("window.bad") is None
        with page.expect_download() as pending:
            page.get_by_role("button", name="Download results JSON").click()
        result_file = Path(temporary) / "results.json"
        pending.value.save_as(result_file)
        result = json.loads(result_file.read_text(encoding="utf-8"))
        assert result["best"]["evaluation"]["days"][0]["cost"] == 4208400
        assert result["configuration"]["planning"]["servings"][0] == 501
        assert result["configuration"]["catalog"][0]["ingredients"][1]["unit"] == "g"
        with page.expect_download() as pending:
            page.get_by_role("button", name="Download results CSV").click()
        csv_file = Path(temporary) / "results.csv"
        pending.value.save_as(csv_file)
        rows = list(csv.DictReader(io.StringIO(csv_file.read_text(encoding="utf-8"))))
        assert any(row["id"] == "salt" and row["unit"] == "g" for row in rows)
        with page.expect_download() as pending:
            page.locator("#export-configuration").click()
        configuration_file = Path(temporary) / "configuration.json"
        pending.value.save_as(configuration_file)
        exported = json.loads(configuration_file.read_text(encoding="utf-8"))
        assert exported["algorithm"]["seed"] == 42
        page.locator("#reset-configuration").click()
        page.wait_for_function(
            "document.querySelector('#save-status').textContent.includes('restored')"
        )
        assert page.locator("#servings-0").input_value() == "500"
        page.locator("#import-configuration").set_input_files(str(configuration_file))
        page.wait_for_function(
            "document.querySelector('#notice').textContent.includes('imported')"
        )
        assert page.locator("#servings-0").input_value() == "501"
        page.locator("#import-configuration").set_input_files(
            {"name": "bad.json", "mimeType": "application/json", "buffer": b"{bad"}
        )
        page.wait_for_function(
            "document.querySelector('#error').textContent.includes('not valid JSON')"
        )
        assert page.locator("#servings-0").input_value() == "501"
        page.locator("#add-component").click()
        assert page.locator("#catalog-list .catalog-card").count() == 20
        page.locator("#delete-component-19").click()
        assert page.locator("#catalog-list .catalog-card").count() == 19
        for index in range(4, 9):
            card = page.locator(".catalog-card").nth(index)
            card.locator("summary").click()
            page.locator(f"#component-{index}-tags").fill("blocked")
        page.locator("#exclusions").fill("blocked")
        page.locator("#evaluate-preview").click()
        page.wait_for_function(
            "document.querySelector('#error').textContent.includes('No eligible components for: protein')"
        )
        page.evaluate("localStorage.setItem('bca.configuration.v1', '{bad')")
        page.reload()
        page.wait_for_function(
            "document.querySelector('#notice').textContent.includes('unreadable')"
        )
        assert page.locator("#servings-0").input_value() == "500"
        page.set_viewport_size({"width": 360, "height": 780})
        assert page.evaluate(
            "document.documentElement.scrollWidth <= window.innerWidth"
        )
        page.locator("#evaluate-preview").click()
        page.locator("#preview-results .result-day").first.wait_for()
        assert page.evaluate(
            "document.documentElement.scrollWidth <= window.innerWidth"
        )
        storage_page = context.new_page()
        storage_page.add_init_script(
            "Object.defineProperty(window, 'localStorage', {get(){throw new Error('unavailable')}})"
        )
        storage_page.goto(args.url + "/static/planner.html")
        storage_page.wait_for_function(
            "document.querySelector('#notice').textContent.includes('storage is unavailable')"
        )
        storage_page.locator("#save-configuration").click()
        storage_page.wait_for_function(
            "document.querySelector('#save-status').textContent.includes('download to preserve')"
        )
        assert not failures, failures
        browser.close()
    print(
        "Planner browser checks passed: edits, saved settings, safe preview, imports, JSON/CSV downloads, unit totals, empty-category errors, storage fallback and 360px layout."
    )


if __name__ == "__main__":
    main()
