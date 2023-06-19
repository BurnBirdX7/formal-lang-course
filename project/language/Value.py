from typing import Iterable, Any, Set

from pyformlang.finite_automaton import EpsilonNFA


class Value:
    pass


class TupleValue(Value):
    def __init__(self, value: Iterable[Any]):
        self.value = list(value)

    def __str__(self):
        val = map(str, self.value)
        return "[ " + ", ".join(val) + " ]"


class FAValue(Value):
    def __init__(self, fa: EpsilonNFA):
        self.value = fa

    def __str__(self):
        starts = f"starts: {SetValue(self.value.start_states)}\n"
        finals = f"finals: {SetValue(self.value.final_states)}\n"
        symbol = f"symbols: {SetValue(self.value.symbols)}\n"
        return f"FA: {self.value}\n" + starts + finals + symbol + "\t"


class SetValue(Value):
    def __init__(self, value: Set[Any]):
        self.value = value

    def __str__(self):
        val = map(str, self.value)
        return "{ " + ", ".join(val) + " }"
