"""顺序、互斥分支与控制流出口的耗时区间。"""

from dataclasses import dataclass, field

from app.modules.action_timing import source_state as state


@dataclass(frozen=True)
class Cost:
    lower: float = 0
    upper: float | None = 0

    def plus(self, other):
        return Cost(
            self.lower + other.lower,
            None if self.upper is None or other.upper is None else self.upper + other.upper,
        )


ZERO = Cost()
UNKNOWN = Cost(0, None)


def choice(left, right):
    if left is None:
        return right
    if right is None:
        return left
    return Cost(
        min(left.lower, right.lower),
        None if left.upper is None or right.upper is None else max(left.upper, right.upper),
    )


def add(left, right):
    return left.plus(right) if left is not None and right is not None else None


@dataclass
class Flow:
    live: Cost | None = ZERO
    returned: Cost | None = None
    broken: Cost | None = None
    continued: Cost | None = None
    states: dict = field(default_factory=dict)

    def with_state(self, channel, bindings):
        self.states[channel] = dict(bindings)
        return self

    def merge_states(self, other):
        result = {}
        for channel in self.states.keys() | other.states.keys():
            branches = [part[channel] for part in (self.states, other.states) if channel in part]
            merged = {}
            state.merge(merged, branches)
            result[channel] = merged
        return result

    def then(self, other):
        return Flow(
            add(self.live, other.live),
            choice(self.returned, add(self.live, other.returned)),
            choice(self.broken, add(self.live, other.broken)),
            choice(self.continued, add(self.live, other.continued)),
            self.merge_states(other),
        )

    def cost(self):
        return choice(choice(self.live, self.returned), choice(self.broken, self.continued)) or ZERO

    def merge(self, other):
        return Flow(
            *(
                choice(getattr(self, key), getattr(other, key))
                for key in ("live", "returned", "broken", "continued")
            ),
            self.merge_states(other),
        )

    def prefix(self, cost):
        return Flow(
            *(add(cost, getattr(self, key)) for key in ("live", "returned", "broken", "continued")),
            self.states,
        )
