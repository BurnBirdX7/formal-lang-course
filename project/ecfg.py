import re
from collections import defaultdict
from typing import Set, Optional, Dict, List, AbstractSet
from pyformlang.cfg import CFG, Variable
from pyformlang.regular_expression import Regex

from project.rfa import RFA, RFABox


class ECFGProduction:
    def __init__(self, head: Variable, body: Regex):
        self.head: Variable = head
        self.body: Regex = body

    def __repr__(self):
        return f"ECFGProduction({self.head!r}, {self.body!r})"

    def __str__(self):
        return f"{self.head!s} -> {self.body!s}"


class ECFG:
    def __init__(
        self,
        start_symbol: Variable,
        variables: Optional[AbstractSet[Variable]] = None,
        productions: Optional[Set[ECFGProduction]] = None,
    ):
        self._start_symbol = start_symbol
        self._vars = variables or set()
        self._productions = productions or set()

    def __repr__(self):
        return (
            f"ECFG(start_symbol={self._start_symbol!r},"
            f"variables={self._vars!r},"
            f"productions={self._productions!r})"
        )

    def __str__(self):
        return "\n".join([str(prod) for prod in self._productions])

    @staticmethod
    def from_text(text: str, start_symbol=Variable("S")) -> "ECFG":
        """
        Constructs ECFG from text
        """

        variables: Set[Variable] = set()
        productions: Dict[Variable, Regex] = dict()

        for line in text.splitlines():
            line = line.strip()
            if line == "":
                continue

            line_arr = line.split("->")
            if len(line_arr) != 2:
                raise RuntimeError(f'Invalid production: "{line}"')

            head_str: str = line_arr[0]
            body_str: str = line_arr[1]

            head = Variable(head_str.strip())
            body = Regex(body_str.strip())

            if head in productions:
                productions[head] = productions[head].union(body)
            else:
                productions[head] = body
                variables.add(head)

            return ECFG(
                start_symbol=start_symbol,
                variables=variables,
                productions={ECFGProduction(k, v) for k, v in productions},
            )

    @staticmethod
    def from_file(name: str, start_symbol: Variable = Variable("S")):
        with open(name) as file:
            return ECFG.from_text(file.read(), start_symbol)

    @staticmethod
    def from_cfg(cfg: CFG) -> "ECFG":
        """
        Converts CFG into ECFG
        """

        productions: Dict[Variable, List[str]] = defaultdict(list)

        for prod in cfg.productions:
            if prod.body:
                productions[prod.head].append(
                    " ".join(re.escape(sym.value) for sym in prod.body)
                )
            else:
                productions[prod.head].append("$")

        return ECFG(
            start_symbol=cfg.start_symbol,
            variables=cfg.variables,
            productions={
                ECFGProduction(head, Regex(" | ".join(body for body in body_list)))
                for head, body_list in productions.items()
            },
        )

    def to_rfa(self) -> RFA:
        """
        Converts Extended CFG into Recursive Finite Automaton
        :return:
        """
        return RFA(
            start_symbol=self._start_symbol,
            boxes={
                RFABox(
                    prod.head, prod.body.to_epsilon_nfa().to_deterministic().minimize()
                )
                for prod in self._productions
            },
        )
