# How the Bee Search Works

This app demonstrates a **discrete Artificial Bee Colony (ABC)** adaptation. The project is named BCA. A candidate solution is a complete school lunch schedule for Monday through Friday. Every day contains a staple, protein dish, vegetable dish, and fruit, so a schedule contains 20 categorical choices.

## From bees to meal schedules

A food source represents a schedule. An employed bee searches near its own source. An onlooker probabilistically chooses a source based on fitness and searches near it. When repeated improvement attempts fail, an employed bee may become a scout and replace that source with a fresh random schedule.

The roles and phase structure follow [Karaboga's original ABC report](https://abc.erciyes.edu.tr/pub/tr06_2005.pdf). The original work describes numerical optimization. This app adapts local moves to categorical menu substitutions and documents that difference explicitly.

## Why a lower score is better

The objective is a weighted sum of nonnegative, normalized terms:

- **Cost:** the week's total cost divided by its configured budget.
- **Budget:** average daily cost excess divided by each day's budget.
- **Nutrition:** average daily normalized deviations: energy below its minimum or above its maximum, protein below its minimum, and fiber below its minimum.
- **Variety:** protein repetitions and identical-menu repetitions beyond their configured limits, normalized over the five days.
- **Workload:** average daily person-minute excess divided by configured kitchen capacity.

Nutrition values are evaluated for one student's serving. School cost and ingredient quantities use the required daily serving count. Batch workload sums ceiling(servings / batch size) times person-minutes per batch.

The score inspector shows both the normalized term and its weighted contribution. Dietary exclusions and required menu categories define valid candidates. Other preferences contribute penalties. A candidate can therefore be valid while failing to meet some targets.

## Fitness and onlooker selection

For nonnegative objective score S:

    fitness = 1 / (1 + S)
    probability(source i) = fitness(i) / sum(fitness of current sources)

Sources with lower objective scores have higher fitness and greater selection probability. An onlooker draw is probabilistic; it does not always choose the best source. Each displayed probability comes from the host's actual population.

## A cycle

1. **Employed:** propose nearby menu substitutions for each source and evaluate them.
2. **Onlooker:** select sources using their fitness probabilities and evaluate more substitutions.
3. **Scout:** replace sources eligible for abandonment with fresh randomly sampled schedules.
4. **Memory:** retain the best score and schedule found throughout the search.

A candidate replaces its source only when its score strictly improves. An accepted move resets that source's consecutive-failure counter. A failed improvement attempt increments it. The abandonment limit refers to attempts, rather than cycles.

Best-ever memory is independent of the live sources, so a scout replacement cannot erase the best result.

## Stopping and reproducibility

The user can stop a run. Automatic stopping uses the maximum number of cycles or an optional number of cycles without a best-score improvement. Completion explains which condition applied.

A seed determines the host's random sequence. The same catalog, planning inputs, algorithm settings, and seed produce the same results. JSON exports preserve those inputs. Playback speed affects display timing, not the optimization choices.

## What the animation means

The source positions in the colony diagram are a schematic layout. They are not school locations or optimization variables. The actual variables are meal component choices.

Bee motion, highlighted sources, substitutions, acceptance/rejection, failure counters, and scouts are driven by host-generated events. Step requests advance one event. Play repeatedly requests advancement. Pause stops further requests; an already in-flight request may finish. The browser renders events and never runs the optimizer.

## MBG framing and demonstration data

The school menu example is inspired by Indonesia's Makan Bergizi Gratis program. BGN describes [the program and student recipients](https://www.bgn.go.id/news/artikel/bgn-akan-memulai-program-mbg-secara-bertahap) and [complete menus including staple food, side dishes, vegetables, and fruit](https://www.bgn.go.id/news/berita/dapur-gizi-modular-siap-jangkau-wilayah-3t-bgn-pastikan-anak-3t-tak-tertinggal-gizi).

Prices, ingredient amounts, nutrition values, and target defaults supplied with this app are explicitly labeled demonstration data. They are editable. A result reports the targets it meets and any remaining violations. The optimizer returns its best observed schedule, without claiming a guaranteed global optimum.
