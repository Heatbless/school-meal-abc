# 02: Observe and control the real bee search

**What to build:** A user starts a seeded search and observes employed, onlooker and scout events with controls and a live best schedule in the browser.

**Blocked by:** 01

**Status:** complete

- [x] Actual discrete ABC phases and documented source-guided substitutions
- [x] Correct fitness selection, greedy counters, scouts and independent best memory
- [x] Cycle/patience/stop termination, deterministic seed
- [x] Host step/snapshot/stop/delete routes and isolation
- [x] Responsive hive animation, source selection, comparisons, convergence and event log
- [x] Play/pause/step/speed/reset controls
- [x] Public algorithm and HTTP tests pass

Evidence: approved colony/HTTP seams cover replay, actual pre-draw probabilities, greedy counters, scout memory, patience, independently enumerated tiny optimum, thread-safe advancement and bounded storage. Installed Chrome validation exercised initialization, employed/onlooker/scout events, SVG bee visibility, play, completion, reset and a 390px phone viewport without page errors or horizontal overflow. Reads do not advance the colony; the browser never optimizes or evaluates meal scores.

See ../spec.md, ../design.md and ../contract.md for the full agreed requirements.
