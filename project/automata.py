from typing import Iterable

import networkx as nt
from pyformlang.finite_automaton import (
    DeterministicFiniteAutomaton,
    NondeterministicFiniteAutomaton,
)
from pyformlang.regular_expression import Regex


def get_dfa_from_regex(regex: str) -> DeterministicFiniteAutomaton:
    """
    Builds DFA from regular expression passed as a string
    """
    return Regex(regex).to_epsilon_nfa().minimize()


def get_nfa_from_graph(
    graph: nt.MultiDiGraph,
    start_states: Iterable | None = None,
    final_states: Iterable | None = None,
) -> NondeterministicFiniteAutomaton:
    """
    Builds NFA from networkx grapg
    :param graph: networkx graph
    :param (optional) start_states: any iterable that contains start states
    :param (optional) final_states: any iterable that contains final states
    :return: NFA
    """

    if start_states is None:
        start_states = set(graph.nodes)
    if final_states is None:
        final_states = set(graph.nodes)

    nfa = DeterministicFiniteAutomaton.from_networkx(graph)

    for ss in start_states:
        nfa.add_start_state(ss)

    for fs in final_states:
        nfa.add_final_state(fs)

    return nfa
