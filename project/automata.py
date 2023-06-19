import sys

import networkx as nt
from numpy import kron
from scipy.sparse import dok_matrix

import project.utils
from typing import Iterable, Union, Optional, Dict, Any, Set, Tuple
from pyformlang.finite_automaton import *
from pyformlang.regular_expression import Regex


def get_dfa_from_regex(regex: str) -> DeterministicFiniteAutomaton:
    """
    Builds DFA from regular expression passed as a string
    """
    return Regex(regex).to_epsilon_nfa().minimize()


def get_nfa_from_graph(
    graph: Union[nt.MultiDiGraph, str],
    start_states: Optional[Iterable[State]] = None,
    final_states: Optional[Iterable[State]] = None,
) -> EpsilonNFA:
    """
    Builds NFA from networkx grapg
    :param graph: networkx graph or name of the graph in CFPQ dataset
    :param (optional) start_states: any iterable that contains start states
    :param (optional) final_states: any iterable that contains final states
    :return: NFA
    """

    if type(graph) == str:
        graph: nt.MultiDiGraph = project.utils.get_graph_by_name(graph)

    nodes = graph.nodes
    if start_states is None:
        start_states = set(nodes)
    if final_states is None:
        final_states = set(nodes)

    nfa = EpsilonNFA.from_networkx(graph)

    for ss in start_states:
        nfa.add_start_state(ss)

    for fs in final_states:
        nfa.add_final_state(fs)

    return nfa


def nfa_get_matrix(dfa: EpsilonNFA):
    """
    Returns adjacency matrices for single DFA
    """
    matrix = dict()
    dfa_dict = dfa.to_dict()
    states_len = len(dfa.states)

    state_idx = {state: idx for idx, state in enumerate(dfa.states)}

    for state_from, transition in dfa_dict.items():
        for label, states_to in transition.items():
            if not isinstance(states_to, set):
                states_to = {states_to}

            for state_to in states_to:
                index_from = state_idx[state_from]
                index_to = state_idx[state_to]
                if label not in matrix:
                    matrix[label] = dok_matrix((states_len, states_len), dtype=bool)
                matrix[label][index_from, index_to] = True
    return matrix, state_idx


def nfa_from_string(string: str) -> EpsilonNFA:
    fa = EpsilonNFA()
    fa.add_start_state(State(0))
    fa.add_final_state(State(1))
    fa.add_transition(State(0), Symbol(string), State(1))
    return fa


def nfa_get_max_state(fa: EpsilonNFA) -> EpsilonNFA:
    max_state = None
    for s in fa.states:
        val = s.value
        if type(s.value) != int:
            raise ValueError("Union possible only for int states")
        if max_state is None:
            max_state = val
        elif max_state < val:
            max_state = val
    return max_state + 1


def nfa_closure(fa: EpsilonNFA) -> EpsilonNFA:
    fa = fa.copy()
    for start in fa.start_states:
        for finals in fa.final_states:
            fa.add_transition(finals, Epsilon(), start)

    return fa


def nfa_union(fa1: EpsilonNFA, fa2: EpsilonNFA) -> EpsilonNFA:
    max_state_1 = nfa_get_max_state(fa1)
    fa3 = fa1.copy()
    for u, label, v in fa2:
        fa3.add_transition(u.value + max_state_1, label, v.value + max_state_1)
    for v in fa2.start_states:
        fa3.add_start_state(v.value + max_state_1)
    for v in fa2.final_states:
        fa3.add_final_state(v.value + max_state_1)
    return fa3


def nfa_concat(fa1: EpsilonNFA, fa2: EpsilonNFA) -> EpsilonNFA:
    max_state_1 = nfa_get_max_state(fa1)
    fa3 = EpsilonNFA()
    for t in fa1:
        fa3.add_transition(*t)
    for v, label, u in fa2:
        fa3.add_transition(v.value + max_state_1, label, u.value + max_state_1)

    for state in fa1.start_states:
        fa3.add_start_state(state)

    for state in fa1.final_states:
        fa3.add_final_state(state)

    for final1 in fa1.final_states:
        for start2 in fa2.start_states:
            fa3.add_transition(final1, Epsilon(), start2)

    return fa3


def nfa_production(fa1: EpsilonNFA, fa2: EpsilonNFA) -> EpsilonNFA:
    """
    Creates production (IDK if it's a correct word) of two FA's
    State of new FA is production of states of FA1 and FA2

    :param fa1: First finite automaton
    :param fa2: Second finite automaton

    :returns Intersection of two finite automatons
    """
    mat1, state1_idx = nfa_get_matrix(fa1)
    mat2, state2_idx = nfa_get_matrix(fa2)
    fa2_state_count = len(state2_idx)
    states1 = {i: k for k, i in state1_idx.items()}
    states2 = {i: k for k, i in state2_idx.items()}
    common_symbols = set(mat1.keys()).intersection(mat2.keys())

    common_matrices = {l: kron(mat1[l], mat2[l]) for l in common_symbols}

    result = EpsilonNFA()

    for symb, mat in common_matrices.items():
        from_idx, to_idx = mat.nonzero()
        for fro, to in zip(from_idx, to_idx):
            from1 = states1[fro // fa2_state_count]
            to1 = states1[to // fa2_state_count]
            from2 = states2[fro % fa2_state_count]
            to2 = states2[to % fa2_state_count]
            result.add_transition(State((from1, from2)), symb, State((to1, to2)))

    for s1 in fa1.start_states:
        for s2 in fa2.start_states:
            result.add_start_state(State((s1, s2)))

    for s1 in fa1.final_states:
        for s2 in fa2.final_states:
            result.add_final_state(State((s1, s2)))

    return result


def nfa_reachability_matrix(matrices: Dict[Any, dok_matrix]) -> Set[Tuple[Any, Any]]:
    flat = None
    for mat in matrices.values():
        if flat is None:
            flat = mat
            continue
        flat |= mat
    if flat is None:
        return set()

    prev = 0
    while flat.count_nonzero() != prev:
        prev = flat.count_nonzero()
        flat += flat @ flat

    from_idx, to_idx = flat.nonzero()
    return set(zip(from_idx, to_idx))


def nfa_reachable(fa: EpsilonNFA) -> Set[Tuple[Any, Any]]:
    matrices, state_idx = nfa_get_matrix(fa)
    reachable = nfa_reachability_matrix(matrices)
    rev_idx = {i: k for k, i in state_idx.items()}
    result = set()
    for u, v in reachable:
        from_id = rev_idx[u]
        to_id = rev_idx[v]
        if from_id in fa.start_states and to_id in fa.final_states:
            result.add((from_id.value, to_id.value))
    return result
