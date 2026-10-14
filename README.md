# ABC · MBG Meal Laboratory

An interactive school meal scheduler that makes the Artificial Bee Colony search visible. Plan one complete lunch for each school day, Monday-Friday, and watch employed bees, onlookers, and scouts improve candidate schedules.

All optimization and scoring run on the Python host. The browser displays events and sends controls, so phones and other computers can use the host over the same network.

## Install with pip

Python 3.11 or newer is required. Create a virtual environment, install the app dependencies, and start the host:

**Windows PowerShell**

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

**macOS / Linux**

```sh
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

Open **http://127.0.0.1:8000**. To allow other devices on your local network, start with `python main.py --host 0.0.0.0 --port 8000` and open `http://<HOST-IP>:8000` from those devices. Keep the Python host running while using the app.

To run development checks, install `requirements-dev.txt` in the activated environment. Then use `python -m pytest` and `ruff check .`.

## Run with uv

Python 3.11 is supported and remains pinned in this project.

```powershell
uv sync
uv run main.py
```

Open **http://127.0.0.1:8000**.

To make the app available to other devices on your local network:

```powershell
uv run main.py --host 0.0.0.0 --port 8000
```

On another device, open `http://<HOST-IP>:8000`, using the host computer's LAN address. The devices must be able to reach each other on the network. Keep the Python host running while using the app.

## Use the laboratory

1. Open the planner to review the component catalog and school settings.
2. Set daily serving counts, budget, nutrition profile, dietary exclusions, kitchen capacity, variety limits, and scoring weights.
3. Save the configuration and return to the colony laboratory.
4. Press Step to initialize a run, then play or advance one event at a time. Adjust playback speed, pause to inspect a source, or stop the run.
5. Review the best schedule and its target status. Export the result and purchasing summary, or save catalog/settings as JSON for a repeatable run.

A menu contains a staple, protein dish, vegetable dish, and fruit. The optimizer changes categorical meal choices. Source positions in the animation are a schematic display of the colony.

## What is included

- Five-day menus and editable daily serving counts.
- Per-serving energy, protein and fiber; school-wide costs in rupiah.
- Ingredient totals that retain their units and batch-based kitchen workload.
- Editable catalog, exclusions, priorities and seeded algorithm controls.
- Real employed/onlooker/scout events, source scores and failure counters.
- Play, pause, single-event step, speed control, reset and stop.
- Best-solution memory, convergence history and explicit stopping reasons.
- Target violations shown alongside the best result.
- Responsive local assets and configuration/result exports.

The supplied prices, nutrition values and defaults are **demonstration data**, editable in the planner. They are not official MBG standards. Finding the best observed schedule does not imply that all targets have been satisfied or that the global optimum has been proved.

Two additional protein choices marked `demo` make the scoring tradeoffs visible: a cheap light portion can miss nutrition targets, while a premium dish can exceed both the budget and kitchen capacity. The original menu choices can still form a week that meets the demonstration targets.

Settings are saved in this browser's local storage. A run keeps its own catalog and settings snapshot; edits in another page affect the next run. Reset deletes this tab's run and loads the saved settings. Reloading or returning to the laboratory also retires this tab's previous run and prepares a new run. The host keeps up to 32 runs and expires runs after one hour without requests.

## Algorithm and modularity

The app uses a documented **discrete ABC adaptation**. Local candidates substitute menu components; onlookers use normalized fitness probabilities; scouts replace abandoned sources. The abandonment limit counts consecutive failed improvement attempts, and the best-ever schedule survives source replacement.

The optimizer, meal evaluation, catalog/configuration models, host controls and browser visualization are separated. Runs snapshot their configuration. Browser playback timing does not change the host's seeded search decisions.

See [the algorithm guide](docs/algorithm.md) for score formulas, phases, fitness, animation semantics and references, and [the architecture](docs/architecture.md) for module boundaries. The confirmed [design brief](.scratch/mbg-school-meals/design.md), [specification](.scratch/mbg-school-meals/spec.md), and [interface contract](.scratch/mbg-school-meals/contract.md) document the build.

## Checks

```powershell
uv run pytest
uv run ruff check .
```

The automated checks cover public meal evaluation, independent quantity/scoring fixtures, input errors, colony behavior, seeded reproducibility, stopping and HTTP controls. The integration browser check uses an existing Chrome installation:

```powershell
uv run --with playwright python tests/browser_smoke.py
uv run --with playwright python tests/browser_planner.py --url http://127.0.0.1:8000
```

Start the app before the browser checks. Pass `--url http://127.0.0.1:<PORT>` to use a different host port, or `--browser <PATH>` to use a different installed Chrome executable. The smoke check writes screenshots and downloaded examples to `.scratch/mbg-school-meals/qa/`; use `--output <PATH>` to change that location. It covers live controls, all bee roles, host pause, configuration snapshots, reproducibility, tab cleanup, exports and 390/360px layouts. The planner check covers catalog and ingredient editing, imports and input validation.
