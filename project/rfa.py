from typing import Optional, Iterable, List
from pyformlang.cfg import Variable
from pyformlang.finite_automaton import DeterministicFiniteAutomaton

from scipy.sparse import csr_matrix

from project.automata import nfa_get_matrix


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
        """
        Minimizes RFA by minimizing underlying boxes
        """
        return RFA(self.start_symbol, [box.minimize() for box in self.boxes])

    def get_matrices(self):
        """
        Returns adjacency matrices for the RFA
        """
        return {box.var: RFA.__dfa_get_matrix(box.dfa) for box in self.boxes}

    @staticmethod
    def __dfa_get_matrix(dfa: DeterministicFiniteAutomaton):
        """
        Returns adjacency matrices for single DFA
        """

        matrix, _ = nfa_get_matrix(dfa)
        return matrix
