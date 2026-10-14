# Bee Colony Optimization

This project demonstrates bee colony optimization through a five-day school meal schedule. Its search uses candidate meal schedules represented as food sources and the bee roles below.

## Language

**Meal schedule**:
A complete assignment of one school lunch menu to each day from Monday through Friday.
_Avoid_: Route, placement

**Meal quantity**:
The required number of servings of a scheduled menu for a school on a particular day.

**Menu**:
A complete school meal containing a staple, a protein dish, a vegetable dish, and fruit.

**Menu component**:
A selectable staple, protein dish, vegetable dish, or fruit that contributes to a menu's cost, nutrition, and preparation requirements.

**Serving**:
One student's portion of a complete menu.

**School**:
The group of students covered by a meal schedule, sharing a daily menu and a nutrition target profile within one planning run.

**Ingredient total**:
The quantity of an ingredient required across the scheduled menus and serving counts.

**Nutrition target profile**:
The energy range, minimum protein, and minimum fiber expected in one serving of a school meal.

**Kitchen workload**:
The estimated person-minutes of work required to prepare a daily menu at its required meal quantity, accounting for preparation batches.

**Target violation**:
A measured departure from a configured budget, nutrition, variety, or kitchen workload target.

**Objective score**:
The weighted measure of a meal schedule's cost and target violations; a lower score represents a better schedule.

**Fitness**:
A positive measure of a food source's attractiveness derived from its objective score; higher fitness makes onlooker selection more likely.

**Food source**:
A candidate solution in the problem's search space. Its quality determines how attractive it is to the colony.

**Employed bee**:
A bee associated with one food source that searches for a better solution near that source.

**Onlooker bee**:
A bee that chooses a food source probabilistically according to its fitness and searches near the selected source.

**Scout bee**:
The role an employed bee takes when its food source is abandoned, searching randomly for a replacement source.

**Abandonment limit**:
The number of consecutive unsuccessful improvement attempts at a food source that makes it eligible for replacement.

**Cycle**:
One pass through the employed bee, onlooker bee, and scout bee phases, with the best solution retained throughout the search.

**Best solution**:
The highest-quality candidate encountered so far during a run, retained even if its original food source is later replaced.
