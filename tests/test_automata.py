import cfpq_data as cfpq
from pyformlang.finite_automaton import DeterministicFiniteAutomaton, State

from project import automata, utils


def test_regex_one_char():
    dfa = automata.get_dfa_from_regex("q")

    test = DeterministicFiniteAutomaton()
    test.add_start_state(State(0))
    test.add_final_state(State(1))
    test.add_transitions([(0, "q", 1)])

    assert dfa == test


def test_regex_two_str():
    dfa = automata.get_dfa_from_regex("qwe | rty")

    test = DeterministicFiniteAutomaton()
    test.add_start_state(State(0))
    test.add_final_state(State(1))
    test.add_transitions([(0, "qwe", 1), (0, "rty", 1)])

    assert dfa == test


def test_regex_inf_q():
    dfa = automata.get_dfa_from_regex("q*")

    test = DeterministicFiniteAutomaton()
    test.add_start_state(State(0))
    test.add_final_state(State(0))
    test.add_transitions([(0, "q", 0)])

    assert dfa == test


def test_nfa_start_final_states_none():
    wc = utils.get_graph_by_name("wc")
    skos_n_nodes = wc.number_of_nodes()

    nfa = automata.get_nfa_from_graph(wc)
    assert skos_n_nodes == len(nfa.start_states)
    assert skos_n_nodes == len(nfa.final_states)


def test_nfa_start_final_states():
    s = {State(3), State(4)}

    wc = utils.get_graph_by_name("wc")
    nfa = automata.get_nfa_from_graph(wc, start_states=s)
    assert nfa.start_states == s


def test_graph_to_nfa():
    cycles = cfpq.labeled_two_cycles_graph(2, 2, labels=("b", "b"))

    nfa = automata.get_nfa_from_graph(
        cycles, start_states={State(0)}, final_states={State(0)}
    )
    dfa = automata.get_dfa_from_regex("(b b b)*")

    assert dfa.is_equivalent_to(nfa)
