# 04: Complete and verify the school meal laboratory

**What to build:** The completed app combines planning, catalog editing, animated search and result exports with setup and algorithm documentation.

**Blocked by:** 02, 03

**Status:** resolved

- [x] Shared editor and lab work without losing inputs
- [x] Entire actual browser control workflow and narrow viewport verified
- [x] Independent tiny exhaustive check and full automated suite pass
- [x] Demo data/defaults labeled and unmet targets clear
- [x] README uv/local-network instructions, architecture/formulas/discrete-ABC documentation
- [x] Standards and spec review findings fixed

See ../spec.md, ../design.md and ../contract.md for the full agreed requirements.

Integration evidence: 39 pytest tests and Ruff pass. `tests/browser_smoke.py`
passes real Chrome checks for saved settings, immutable host run snapshots,
all three bee roles, actual pause, completion, reset/replay, stop, tab navigation
and reload cleanup, configuration/result JSON and CSV downloads, malformed data,
390/360px layouts and no browser errors. `tests/browser_planner.py` passes after
catalog/result integration. Screenshots and downloaded examples are generated
under `.scratch/mbg-school-meals/qa/` (ignored artifacts).

Final integration verification: 39 tests pass, Ruff passes, Chrome workflows pass, and independent Standards and Spec reviews report zero findings. See ../review.md.
