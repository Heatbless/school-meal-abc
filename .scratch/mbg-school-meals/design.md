# BCA: Five-day MBG School Meal Scheduler

Status: confirmed by user; implementation authorized with uv and Python 3.11

## Purpose

Build a complete, modular Python application that demonstrates a discrete Artificial Bee Colony (ABC) algorithm through five-day MBG school meal scheduling. BCA remains the project name. The everyday example involves meal choices and scheduling. TSP and placement optimization are excluded by the user's requirements.

The application combines an understandable school-scale planning result with an animation driven by the optimizer's real decisions. Sample prices, nutrition values, and targets are labeled demonstration inputs; users can edit them.

## Confirmed problem model

- One school per run, with one lunch per student on each weekday, Monday through Friday.
- Adjustable daily serving counts, initially 500 each day.
- One nutrition target profile per run, evaluated per serving.
- Each daily menu includes a staple, a protein dish, a vegetable dish, and fruit.
- Each food source represents a complete five-day schedule, containing 20 component choices.
- Required serving counts are inputs to the planner.
- Costs and ingredient quantities scale to the school serving counts.
- Preparation estimates use component batch sizes and work per batch, reported in person-minutes.

## Catalog and inputs

Include an immediately usable sample catalog of Indonesian-style meal components. Each component has a stable identifier, name, category, cost per serving in rupiah, energy, protein, fiber, dietary/allergen tags, ingredient quantities per serving, batch size, and work per batch.

Provide catalog editing and the ability to add components. Settings include daily serving counts, per-serving budget, nutrition targets, dietary exclusions, daily kitchen capacity, variety preferences, scoring weights, and algorithm controls. Provide JSON import/export for reproducible catalog and configuration snapshots.

Filter excluded components before search. A schedule must select one allowed component from each required category each day. Explain missing eligible categories and invalid inputs before initialization.

## Scoring

Minimize a nonnegative weighted score with separately visible contributions for cost, budget overruns, nutrition shortfalls or excesses, repetition, and kitchen workload overruns.

Normalize contributions against the configured targets so rupiah amounts do not overwhelm nutrition or workload penalties solely because of their units. Show the normalization and weights in the algorithm explanation.

- Nutrition: sum component values per serving; measure energy below/above its range, protein below its minimum, and fiber below its minimum.
- School cost: per-serving component costs multiplied by required daily servings, with daily and five-day totals.
- Budget: show daily and weekly budget totals and overruns.
- Variety: use an editable limit on repeated protein dishes and repeated identical menus; explain every repetition penalty.
- Workload: sum `ceil(servings / batch_size) * work_per_batch` over the daily components, then compare with daily kitchen capacity.
- Ingredients: aggregate quantities by ingredient identifier and unit; do not combine incompatible units.

Use `fitness = 1 / (1 + objective_score)` and normalize the population's fitness values into onlooker selection probabilities.

Always report which targets are satisfied and which remain unmet. Return the best schedule found even when some soft targets remain unmet. The final result includes the achieved score and its component breakdown.

## Proposed editable demonstration defaults

These numerical defaults are implementation recommendations for the demonstration, rather than MBG standards.

| Setting | Starting value |
| --- | --- |
| Daily servings | 500 on each weekday |
| Budget | Rp10,000 per student per meal |
| Energy | 500-750 kcal per serving |
| Protein | At least 20 g per serving |
| Fiber | At least 6 g per serving |
| Kitchen capacity | 600 person-minutes per day |
| Protein repetition | At most twice across the week |
| Identical menu repetition | At most once across the week |
| Food sources / employed bees | 16 |
| Onlooker attempts per cycle | 16 |
| Abandonment limit | 40 consecutive failed improvement attempts |
| Maximum cycles | 100 |
| Optional stopping patience | 20 cycles without best-score improvement |
| Random seed | 42 |

Expose scoring weights with sensible defaults and preserve every weight in exported run settings.

## Discrete ABC behavior

1. Initialize random valid schedules from the eligible catalog and retain the best.
2. Employed phase: each employed bee proposes a neighboring schedule by substituting one component choice. Retain a strictly better candidate; otherwise increment the source's failure counter. An improvement resets that counter.
3. Onlooker phase: show normalized selection probabilities, select sources probabilistically, propose substitutions, and apply the same improvement rule.
4. Scout phase: replace a source eligible for abandonment with a randomly generated valid schedule. Make the replacement and counter reset visible.
5. Retain best-ever results independently of current source replacement.
6. Stop at the maximum cycle count, optional best-score stagnation limit, or user stop; show the stopping reason.

Document how discrete substitutions adapt numerical ABC to categorical meal choices. Use distinct partner sources for source-guided proposals where applicable, and preserve randomness through an explicitly seeded generator.

## Animation and interaction

Display the hive, source population, and distinct bee roles alongside the selected five-day schedule. Source screen positions are a schematic display of the population; the optimization variables are the meal choices.

Every animation reflects a host-produced algorithm event. Explain the active phase, chosen source, proposed day/component change, candidate score, acceptance or rejection, failure counter, onlooker probabilities, scout replacement, and best-ever score.

Provide play, pause, single-event step, speed control, reset, and stop. While paused, advancement resumes only after a control request. Include a readable event log and convergence chart, with reduced animation suitable for small screens or motion preferences.

The final view includes daily menus, serving counts, per-serving nutrition, school-scale costs, component quantities, estimated ingredient totals, kitchen workload, target violations, and a five-day purchasing summary. Provide downloadable results and settings.

## Modularity and hosting

All optimization and scoring execute on the Python host. Browsers submit inputs and controls and render host results and events. Other devices can access the host over the local network.

Separate the reusable bee algorithm, meal scheduling/scoring, catalog data, run control/event delivery, and browser visualization. Keep algorithm state independent of display timing and network transport. Snapshot catalog/settings at run creation for consistent, repeatable runs.

Implementation recommendation: Python web server with a responsive HTML/CSS/JavaScript interface and lightweight vector/canvas animation. Choose supporting libraries during implementation and document installation and host/network startup commands.

## Completion evidence

Deliver meaningful automated checks for score calculations, quantity scaling, batch workload, dietary filtering, discrete candidate validity, onlooker selection, abandonment, best-result retention, stopping, seeded reproducibility, and host control behavior. Check a small optimization fixture against exhaustive enumeration where practical.

Validate the browser flow through settings, catalog editing, initialization, all bee phases, pause/step/reset, completion, and result export. Include setup instructions, modular architecture notes, the discrete ABC explanation and formulas, and references to the algorithm and MBG framing.

## Context references

- ABC algorithm creator's reference: https://abc.erciyes.edu.tr/
- BGN MBG introduction: https://www.bgn.go.id/news/artikel/bgn-akan-memulai-program-mbg-secara-bertahap
- BGN complete-menu description: https://www.bgn.go.id/news/berita/dapur-gizi-modular-siap-jangkau-wilayah-3t-bgn-pastikan-anak-3t-tak-tertinggal-gizi
