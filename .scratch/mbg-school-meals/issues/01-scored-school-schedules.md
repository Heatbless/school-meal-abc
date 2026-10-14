# 01: Evaluate and display school meal schedules

**What to build:** An immediately runnable Python host supplies a demonstration catalog and evaluates a five-day schedule. A minimal browser page displays menus, score and school totals.

**Blocked by:** None (can start immediately)

**Status:** complete

- [x] Bootstrap/evaluate HTTP contracts and public MealProblem interface work
- [x] Validated catalog/settings and category eligibility errors
- [x] Correct independent-fixture scoring, quantity/batch aggregation and unit handling
- [x] uv project and runnable minimal interface
- [x] Targeted tests pass

See ../spec.md, ../design.md and ../contract.md for the full agreed requirements.


## Completion evidence
- 28 targeted tests pass at the confirmed MealProblem and HTTP boundaries.
- Independent fixtures cover weighted normalized scoring, per-serving nutrition, school costs, ceil batch workloads, repeated-menu/protein penalties and same-ID incompatible ingredient units.
- Input coverage includes boolean/nonfinite values, tiny positive normalization targets, duplicate IDs, dietary category depletion, wrong schedules, snapshot isolation and a 1000-component catalog.
- Bootstrap includes 19 editable demonstration components; a five-day 500-serving schedule with five distinct proteins meets all original default targets.
- uv run ruff check . passes; uv run main.py --help verifies host/port entry point.
- Positive normalization targets are bounded to 0.001..10,000,000 to keep all scores finite. Other numeric values are nonnegative finite values up to 10,000,000; servings and batch size are positive integers up to 1,000,000.
