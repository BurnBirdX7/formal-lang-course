from typing import Optional, Iterable, List
from pyformlang.cfg import Variable
from pyformlang.finite_automaton import DeterministicFiniteAutomaton


class RFABox:
    """
    Class represents box of RFA
    """

    def __init__(
        self,
        variable: Optional[Variable] = None,
        dfa: Optional[DeterministicFiniteAutomaton] = None,
    ):
        self._var = variable
        self._dfa = dfa

    def __eq__(self, other: "RFABox"):
        if not isinstance(self, RFABox):
            return False  # types aren't checked on runtime
        return self._var == other._var and self._dfa.is_equivalent_to(other)

    def minimize(self) -> "RFABox":
        """
        Minimizes underlying DFA
        """
        return RFABox(self._var, self._dfa.minimize())

    @property
    def var(self) -> Variable:
        return self._var

    @property
    def dfa(self) -> DeterministicFiniteAutomaton:
        return self._dfa


class RFA:
    """
    RFA - Recursive Finite Automaton
    """

    def __init__(self, start_symbol: Variable, boxes: Iterable[RFABox]):
        self.start_symbol = start_symbol
        self.boxes = boxes

    def minimize(self) -> "RFA":
        return RFA(self.start_symbol, [box.minimize() for box in self.boxes])
