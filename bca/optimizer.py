"""Seeded discrete ABC. Advancement, not browser time, changes the colony."""

from copy import deepcopy
from random import Random
from threading import RLock

from .models import Algorithm


class BeeColony:
    """A problem supplies sample, neighbor and evaluate; the colony knows no meals."""

    def __init__(self, problem, algorithm):
        self.problem = problem
        self.settings = Algorithm.model_validate(
            algorithm.model_dump() if isinstance(algorithm, Algorithm) else algorithm
        )
        self.rng = Random(self.settings.seed)
        self.lock = RLock()
        self.status, self.phase, self.cycle = "ready", "initialization", 0
        self.sequence = self.evaluations = 0
        self.sources, self.history = [], []
        self.best, self.stop_reason = None, None
        self._events = self._search()

    def _evaluate(self, schedule):
        evaluation = self.problem.evaluate(schedule)
        self.evaluations += 1
        if self.best is None or evaluation["score"] < self.best["evaluation"]["score"]:
            self.best = deepcopy({"schedule": schedule, "evaluation": evaluation})
        return evaluation

    def _source(self, index, schedule):
        evaluation = self._evaluate(schedule)
        return {
            "index": index,
            "schedule": list(schedule),
            "score": evaluation["score"],
            "fitness": evaluation["fitness"],
            "trials": 0,
            "evaluation": evaluation,
        }

    def _probabilities(self):
        total = sum(source["fitness"] for source in self.sources)
        return [source["fitness"] / total for source in self.sources]

    def _event(self, type, message, **data):
        self.sequence += 1
        return dict(
            seq=self.sequence,
            type=type,
            cycle=self.cycle,
            phase=self.phase,
            message=message,
            **data,
        )

    def _attempt(self, index, role, probabilities=None, draw=None):
        source = self.sources[index]
        partner = self.rng.choice([i for i in range(len(self.sources)) if i != index])
        old_schedule, old_score = list(source["schedule"]), source["score"]
        previous_evaluation = source["evaluation"]
        candidate = self.problem.neighbor(
            old_schedule, self.sources[partner]["schedule"], self.rng
        )
        position = next(
            (i for i, (a, b) in enumerate(zip(old_schedule, candidate)) if a != b), None
        )
        evaluation = self._evaluate(candidate)
        accepted = evaluation["score"] < old_score
        if accepted:
            source.update(
                schedule=list(candidate),
                score=evaluation["score"],
                fitness=evaluation["fitness"],
                trials=0,
                evaluation=evaluation,
            )
        else:
            source["trials"] += 1
        return self._event(
            "attempt",
            f"{role.capitalize()} bee tried source {index + 1}: "
            f"{'accepted improvement' if accepted else 'no improvement'}.",
            role=role,
            source=index,
            partner=partner,
            position=position,
            previous_component=old_schedule[position] if position is not None else None,
            candidate_component=candidate[position] if position is not None else None,
            old_score=old_score,
            candidate_score=evaluation["score"],
            accepted=accepted,
            trials=source["trials"],
            candidate_evaluation=evaluation,
            previous_evaluation=previous_evaluation,
            probabilities=probabilities,
            draw=draw,
        )

    def _search(self):
        self.status = "running"
        self.sources = [
            self._source(i, self.problem.sample(self.rng))
            for i in range(self.settings.sources)
        ]
        self.history.append({"cycle": 0, "score": self.best["evaluation"]["score"]})
        yield self._event(
            "initialized", f"Initialized {len(self.sources)} valid meal schedules."
        )
        stagnant = 0
        for cycle in range(1, self.settings.max_cycles + 1):
            self.cycle = cycle
            previous_best = self.best["evaluation"]["score"]
            self.phase = "employed"
            for index in range(len(self.sources)):
                yield self._attempt(index, "employed")
            self.phase = "onlooker"
            for _ in range(self.settings.onlookers):
                probabilities = self._probabilities()
                draw = self.rng.random()
                cumulative, index = 0.0, len(self.sources) - 1
                for candidate_index, probability in enumerate(probabilities):
                    cumulative += probability
                    if draw < cumulative:
                        index = candidate_index
                        break
                yield self._attempt(index, "onlooker", probabilities, draw)
            self.phase = "scout"
            yield self._event(
                "phase", "Scout phase: check sources against the abandonment limit."
            )
            for index, source in enumerate(self.sources):
                if source["trials"] >= self.settings.limit:
                    abandoned = deepcopy(source)
                    self.sources[index] = self._source(
                        index, self.problem.sample(self.rng)
                    )
                    yield self._event(
                        "scout",
                        f"Scout replaced source {index + 1} after "
                        f"{abandoned['trials']} unsuccessful attempts.",
                        role="scout",
                        source=index,
                        abandoned=abandoned,
                        replacement=deepcopy(self.sources[index]),
                    )
            self.phase = "memory"
            score = self.best["evaluation"]["score"]
            self.history.append({"cycle": cycle, "score": score})
            stagnant = stagnant + 1 if score >= previous_best else 0
            yield self._event(
                "cycle", f"Cycle {cycle} complete. Best score: {score:.4f}."
            )
            if self.settings.patience and stagnant >= self.settings.patience:
                self.stop_reason = "patience"
                break
        self.stop_reason = self.stop_reason or "max_cycles"
        self.status, self.phase = "completed", "completed"
        yield self._event(
            "completed", f"Run completed: {self.stop_reason.replace('_', ' ')}."
        )

    def advance(self, steps=1):
        if (
            isinstance(steps, bool)
            or not isinstance(steps, int)
            or not 1 <= steps <= 100
        ):
            raise ValueError("steps must be an integer from 1 to 100")
        with self.lock:
            events = []
            for _ in range(steps):
                if self.status in ("completed", "stopped"):
                    break
                events.append(next(self._events))
            return deepcopy(events)

    def snapshot(self):
        with self.lock:
            probabilities = self._probabilities() if self.sources else []
            return deepcopy(
                {
                    "status": self.status,
                    "phase": self.phase,
                    "cycle": self.cycle,
                    "sequence": self.sequence,
                    "evaluations": self.evaluations,
                    "sources": [
                        dict(source, probability=probabilities[i])
                        for i, source in enumerate(self.sources)
                    ],
                    "best": self.best,
                    "history": self.history,
                    "stop_reason": self.stop_reason,
                }
            )

    def stop(self):
        with self.lock:
            if self.status not in ("completed", "stopped"):
                self.status, self.stop_reason = "stopped", "user"
            return self.snapshot()
