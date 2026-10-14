# MBG School Meal Scheduler
Status: implemented and verified

## Problem Statement
An educational BCA application needs a complete everyday-life optimization example and a faithful animation of its actual decisions. The confirmed example is a five-day MBG school lunch schedule at school-scale quantities. See design.md for the complete confirmed domain requirements and proposed editable defaults.

## Solution
A responsive browser app backed entirely by a Python 3.11 host, managed with uv. Users edit a component catalog and planning inputs, observe a discrete ABC search, and export its best schedule with scores, violations, and purchasing totals.

## User Stories
1. As a learner, I want a usable demo catalog so I can start immediately.
2. As a planner, I want five school lunches so I can plan a school week.
3. As a planner, I want staples, proteins, vegetables and fruit in every menu so the menu is complete.
4. As a planner, I want editable daily serving counts so quantities match school demand.
5. As a planner, I want per-serving nutrition so school size does not distort nutrition scoring.
6. As a planner, I want school-wide costs in rupiah so I can review the budget.
7. As a planner, I want energy, protein and fiber targets so I can express the profile for this run.
8. As a planner, I want dietary exclusions so incompatible components are unavailable.
9. As a planner, I want workload estimates by batch so large quantities are represented.
10. As a planner, I want repetition penalties so the week has variety.
11. As a planner, I want editable priorities so scoring is understandable.
12. As a learner, I want employed attempts displayed so I see local search.
13. As a learner, I want onlooker probabilities displayed so selection is explainable.
14. As a learner, I want scout replacements displayed so I see exploration.
15. As a learner, I want acceptance, rejection and failure counts so I can follow decisions.
16. As a learner, I want a convergence chart so I can see improvement.
17. As a learner, I want play, pause, step, speed, stop and reset so I can examine the search.
18. As a learner, I want a seed so runs are repeatable.
19. As a learner, I want a stopping reason so completion is understandable.
20. As a planner, I want editable catalog data so the example can change.
21. As a planner, I want JSON import/export so catalog and settings are reusable.
22. As a planner, I want menus and procurement totals so the final schedule is useful.
23. As a planner, I want explicit unmet targets so a best score is not mistaken for full target satisfaction.
24. As a phone user, I want a responsive interface so I can view the host's work.
25. As a maintainer, I want the optimizer separated from meal scoring and display so the app is modular.
26. As a user, I want uv startup instructions and tests so the app is runnable and reviewable.

## Implementation Decisions
- Follow design.md and the accompanying interface contract. Four implementation tickets form the dependency graph.
- Use a FastAPI host, Pydantic input validation and local static browser assets. No external CDN is required for the UI.
- All stochastic search and scoring execute on the host. Browser timing requests advancement; pausing stops further advancement requests.
- A run snapshots catalog/settings, and each advance produces actual events and a serializable snapshot.
- Catalog/settings editing is remembered in browser local storage and supported by JSON import/export. Each browser session controls its own host run.
- Inputs are bounded and finite. Use normalized nonnegative score terms and fitness 1/(1+score).
- Preserve best-ever schedules across scout replacement. Counters measure unsuccessful attempts. The result remains valid even if soft targets remain unmet.
- Scoring handles ingredient units explicitly; work per batch is person-minutes.
- Source display positions are schematic. They are not optimization coordinates.

## Testing Decisions
- The confirmed public test seams are meal evaluation, colony advancement/snapshots, and HTTP run controls. Test observable results at these interfaces rather than private helpers.
- Use independently worked literal fixtures for cost, nutrition, batch workload and quantities.
- Use tiny exhaustive enumeration as an independent optimization check.
- Verify replayability, greedy decisions, selection probabilities, scouts, stopping and best retention through public events.
- Verify input errors and isolation through HTTP; validate the real browser workflow and narrow layout.
- Run targeted tests during each slice and the full suite during integration.

## Out of Scope
TSP, placement optimization, official MBG nutritional certification, public hosting deployment, and institutional account management.

## Further Notes
Python 3.11 is already available via uv. Preserve it unless an actual incompatibility requires a change. Numerical defaults are demonstration inputs, not program standards.
