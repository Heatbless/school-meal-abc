# Integration Contract
This contract coordinates the implementation tickets. Changes must be announced to the coordinator and kept compatible with consumers.

## Configuration schema
GET /api/bootstrap returns {catalog, planning, algorithm, categories, days}.
Categories in order: staple, protein, vegetable, fruit. Days: Monday-Friday.
A schedule is a flat list of 20 component IDs: day-major, category-minor.

Component fields:
id, name, category, cost (rupiah/serving), energy (kcal/serving), protein (g/serving), fiber (g/serving), tags (list of strings), ingredients (list of {id, name, quantity, unit}), batch_size (positive integer), work_minutes (person-minutes/batch).
Planning fields:
servings (five positive integers), budget_per_serving (positive number), energy_min, energy_max, protein_min, fiber_min, kitchen_capacity, max_protein_repeats (1..5), max_menu_repeats (1..5), exclusions (list of tags), weights ({cost,budget,nutrition,variety,workload}, nonnegative numbers).
Algorithm fields:
sources (2..80), onlookers (1..160), limit (1..10000), max_cycles (1..2000), patience (0 disables; otherwise 1..2000), seed (integer).
Defaults come from design.md; initial weights cost=1, budget=5, nutrition=8, variety=2, workload=3.

POST /api/evaluate body {catalog, planning, schedule}; returns evaluation.
Evaluation fields:
score, fitness, contributions (weighted cost/budget/nutrition/variety/workload), metrics (unweighted normalized terms), days (five objects), totals, violations (list of readable strings), targets_met (boolean).
Each day: day, servings, components (full component data or component ID/name/category sufficient for rendering), nutrition {energy,protein,fiber}, cost_per_serving, cost, budget, workload, component_quantities (list of {id,name,servings,batches}), ingredients (list of aggregated quantities), violations.
Totals: cost, budget, servings, workload, ingredients (list of {id,name,quantity,unit}).

Python public interfaces: default_configuration() returns a dict; MealProblem(catalog, planning) validates and snapshots its inputs; sample(rng) returns schedule; neighbor(schedule, partner, rng) returns a valid schedule differing by at most one position; evaluate(schedule) returns an evaluation dict. Accept catalog/planning as model objects or documented dictionaries.

## Live runs
POST /api/runs body {catalog,planning,algorithm} -> {id,state}.
GET /api/runs/{id} -> state.
POST /api/runs/{id}/step body {steps:1..100} -> {events,state}.
POST /api/runs/{id}/stop -> state.
DELETE /api/runs/{id} deletes the run.

State fields: status (ready/running/completed/stopped), cycle, phase, sequence, evaluations, sources (list of {index,schedule,score,fitness,probability,trials}), best ({schedule,evaluation}), history (list of {cycle,score}), stop_reason.
Best may be null before initialization.
Events contain seq, type, cycle, phase and a readable message. Attempt events additionally contain role, source, partner, position, previous_component, candidate_component, old_score, candidate_score, accepted, trials, and candidate_evaluation when applicable. Onlooker selection probabilities must be available in the event or state. Scout events identify the abandoned source and replacement. Initialize/cycle/completed events support teaching the phase sequence.
Initialization occurs through the advancement interface and yields an initialization event. Each visible attempt is real. Fast play may request several events per advance; step requests one event.
Expose BeeColony(problem, algorithm) with advance(steps=1), snapshot(), stop(). Randomness is local and seeded.

## Browser modules and route ownership
Ticket 01 owns initial package, models, scoring, data, server bootstrap/evaluate, minimal index, pyproject and tests.
Ticket 02 owns optimizer, live run routes, main lab interface and shared base stylesheet. It must not edit planner.html, planner.js, editor.css, results.js or configuration.js (owned by 03).
Ticket 03 owns configuration.js, planner.html, planner.js, editor.css, results.js and export tests. Avoid app.py edits; host serves static assets under /static and planner.html can be linked directly there.
configuration.js exports loadConfiguration() async (bootstrap fallback plus local storage), saveConfiguration(configuration), resetConfiguration(), and api(path, options={}) with JSON errors.
Local storage key: abc.configuration.v1. Stored value {catalog,planning,algorithm}. Lab and planner share this contract. Existing bca.configuration.v1 data is migrated on first load.
results.js exports renderResults(container, best, configuration) and exportResults(best, configuration, format); it can be imported by the lab after integration. Support JSON and CSV downloads without recalculating optimization in JavaScript.
Ticket 02 initially reads the configuration key directly and renders a basic best schedule; 04 wires shared modules and richer results.
Main index route /; planner link /static/planner.html. Settings link must be present. All UI text must be safely rendered as text, not interpolated untrusted HTML.

## Review and execution
Use uv and Python 3.11. Work in assigned worktrees based on integration branch bca/mbg-school-meals. Read tdd and test the already confirmed seams. Commit only assigned changes; merge integration branch before reporting done. Mark ticket complete only after acceptance checks pass.
