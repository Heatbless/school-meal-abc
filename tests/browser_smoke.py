"""Real host/browser workflow. Start main.py first; run with uv --with playwright.

Uses installed Chrome; --url, --browser and --output are overridable.
"""

import argparse
import csv
import io
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def ready(page, selector):
    page.locator(selector).wait_for(state="visible")
    page.wait_for_function(
        "selector => !document.querySelector(selector).disabled", arg=selector
    )


def click_step(page):
    before = page.locator("#event-count").inner_text()
    page.locator("#step-button").click()
    page.wait_for_function(
        "previous => document.querySelector('#event-count').textContent !== previous",
        arg=before,
    )
    page.wait_for_function("!document.querySelector('#reset-button').disabled")


def download(page, button, output):
    with page.expect_download() as pending:
        button.click()
    pending.value.save_as(output)
    return output.read_text(encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--browser", default="C:/Program Files/Google/Chrome/Application/chrome.exe"
    )
    parser.add_argument("--output", default=".scratch/mbg-school-meals/qa")
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=args.browser, headless=True
        )
        context = browser.new_context(
            accept_downloads=True, viewport={"width": 1440, "height": 1100}
        )
        page = context.new_page()
        errors, events, run_ids = [], [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "console",
            lambda message: (
                errors.append(message.text) if message.type == "error" else None
            ),
        )

        def response(response):
            if (
                response.request.method == "POST"
                and response.url.endswith("/api/runs")
                and response.ok
            ):
                run_ids.append(response.json()["id"])
            if response.url.endswith("/step") and response.ok:
                events.extend(response.json()["events"])

        page.on("response", response)
        page.goto(args.url + "/static/planner.html")
        ready(page, "#save-configuration")
        page.locator("#servings-0").fill("501")
        page.locator("#sources").fill("3")
        page.locator("#onlookers").fill("2")
        page.locator("#limit").fill("1")
        page.locator("#max_cycles").fill("2")
        page.locator("#patience").fill("0")
        page.locator(".catalog-card").first.locator("summary").click()
        page.locator("#component-0-name").fill("Nasi sekolah (edited)")
        page.locator("#save-configuration").click()
        page.wait_for_function(
            "document.querySelector('#save-status').textContent.includes('Saved')"
        )
        saved = json.loads(
            download(
                page,
                page.locator("#export-configuration"),
                output / "configuration.json",
            )
        )
        assert saved["planning"]["servings"][0] == 501
        assert saved["algorithm"]["sources"] == 3
        page.goto(args.url + "/")
        ready(page, "#step-button")
        assert "501 / 500" in page.locator("#scenario-summary").inner_text()
        click_step(page)
        first_id = run_ids[-1]
        initial = context.request.get(args.url + "/api/runs/" + first_id).json()
        assert len(initial["sources"]) == 3
        assert initial["best"]["evaluation"]["totals"]["servings"] == 2501
        assert (
            "edited" in page.locator("#best-result").inner_text()
            or "edited" in page.locator("#selected-source").inner_text()
        )
        page.locator("#source-0").click()
        assert "Source 1" in page.locator("#selected-source").inner_text()
        assert "current chance" in page.locator("#source-0").inner_text()
        # A later saved input changes the next run, never the current snapshot.
        editor = context.new_page()
        editor.goto(args.url + "/static/planner.html")
        ready(editor, "#save-configuration")
        editor.locator("#servings-0").fill("777")
        editor.locator("#save-configuration").click()
        editor.wait_for_function(
            "document.querySelector('#save-status').textContent.includes('Saved')"
        )
        assert context.request.get(args.url + "/api/runs/" + first_id).json() == initial
        click_step(page)
        assert "Previous score" in page.locator("#decision-details").inner_text()
        assert "Candidate score" in page.locator("#decision-details").inner_text()
        page.locator("#speed-control").fill("1")
        page.locator("#play-button").click()
        page.wait_for_function(
            "document.querySelector('#event-count').textContent !== '2 events'"
        )
        page.locator("#pause-button").click()
        page.wait_for_function("!document.querySelector('#reset-button').disabled")
        paused = context.request.get(args.url + "/api/runs/" + first_id).json()
        page.wait_for_timeout(500)
        assert context.request.get(args.url + "/api/runs/" + first_id).json() == paused
        assert "Paused" in page.locator("#run-status").inner_text()
        page.locator("#speed-control").fill("5")
        for _ in range(30):
            if page.locator("#step-button").is_disabled():
                break
            click_step(page)
            if events[-1].get("role") == "onlooker":
                assert page.locator("#probability-panel").is_visible()
                assert page.locator(".probability-row").count() == 3
                assert abs(sum(events[-1]["probabilities"]) - 1) < 1e-10
                page.screenshot(path=str(output / "onlooker-desktop.png"))
        final = context.request.get(args.url + "/api/runs/" + first_id).json()
        assert final["status"] == "completed" and final["stop_reason"] == "max_cycles"
        assert {event.get("role") for event in events} >= {
            "employed",
            "onlooker",
            "scout",
        }
        assert "Completed" in page.locator("#run-status").inner_text()
        assert page.locator("#best-result .result-day").count() == 5
        assert page.locator(".purchasing-summary").is_visible()
        exported = json.loads(
            download(
                page,
                page.get_by_role("button", name="Download results JSON"),
                output / "results.json",
            )
        )
        assert exported["best"] == final["best"]
        assert exported["configuration"]["planning"]["servings"][0] == 501
        assert (
            exported["configuration"]["catalog"][0]["name"] == "Nasi sekolah (edited)"
        )
        rows = list(
            csv.DictReader(
                io.StringIO(
                    download(
                        page,
                        page.get_by_role("button", name="Download results CSV"),
                        output / "results.csv",
                    )
                )
            )
        )
        assert sum(row["section"] == "day" for row in rows) == 5
        assert any(row["section"] == "purchasing" for row in rows)
        page.screenshot(path=str(output / "lab-desktop.png"), full_page=True)
        for width in (390, 360):
            page.set_viewport_size({"width": width, "height": 844})
            assert page.evaluate(
                "document.documentElement.scrollWidth <= innerWidth"
            ), f"Overflow at {width}px"
            assert "\ufffd" not in page.locator("body").inner_text()
            page.screenshot(path=str(output / f"lab-{width}.png"), full_page=True)
            page.evaluate("window.scrollTo(0, 0)")
            page.screenshot(path=str(output / f"lab-{width}-viewport.png"))
        page.locator("#reset-button").click()
        page.wait_for_function(
            "document.querySelector('#event-count').textContent === '0 events'"
        )
        ready(page, "#step-button")
        assert "777 / 500" in page.locator("#scenario-summary").inner_text()
        assert context.request.get(args.url + "/api/runs/" + first_id).status == 404
        click_step(page)
        replay_id = run_ids[-1]
        replay = context.request.get(args.url + "/api/runs/" + replay_id).json()
        page.locator("#reset-button").click()
        page.wait_for_function(
            "document.querySelector('#event-count').textContent === '0 events'"
        )
        ready(page, "#step-button")
        click_step(page)
        assert (
            context.request.get(args.url + "/api/runs/" + run_ids[-1]).json() == replay
        )
        page.locator("#stop-button").click()
        page.wait_for_function(
            "document.querySelector('#run-status').textContent.includes('Stopped')"
        )
        stopped = context.request.get(args.url + "/api/runs/" + run_ids[-1]).json()
        assert stopped["status"] == "stopped" and stopped["stop_reason"] == "user"
        assert page.locator("#step-button").is_disabled()
        # Navigating to the editor and back retires this tab's old run.
        previous_id = run_ids[-1]
        page.locator("#settings-link").click()
        ready(page, "#save-configuration")
        page.goto(args.url + "/")
        ready(page, "#step-button")
        assert context.request.get(args.url + "/api/runs/" + previous_id).status == 404
        click_step(page)
        previous_id = run_ids[-1]
        page.reload()
        ready(page, "#step-button")
        assert context.request.get(args.url + "/api/runs/" + previous_id).status == 404
        # Bad saved data falls back with a visible explanation.
        page.evaluate("localStorage.setItem('abc.configuration.v1', '{bad')")
        page.reload()
        ready(page, "#step-button")
        assert "unreadable" in page.locator("#info-message").inner_text()
        page.goto(args.url + "/static/planner.html")
        ready(page, "#save-configuration")
        page.locator("#import-configuration").set_input_files(
            {"name": "bad.json", "mimeType": "application/json", "buffer": b"{bad"}
        )
        page.wait_for_function(
            "document.querySelector('#error').textContent.includes('not valid JSON')"
        )
        assert page.locator("#servings-0").input_value() == "500"
        assert "\ufffd" not in page.locator("body").inner_text()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(path=str(output / "planner-360.png"), full_page=True)
        page.goto(args.url + "/static/guide.html")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert "\ufffd" not in page.locator("body").inner_text()
        assert not errors, errors
        browser.close()
    print(
        "Browser checks passed: saved inputs/snapshots, all bee roles, controls, true pause, completion, seeded reset, stop, tab run cleanup, JSON/CSV downloads, malformed data, desktop/390/360px layout, and no browser errors."
    )


if __name__ == "__main__":
    main()
