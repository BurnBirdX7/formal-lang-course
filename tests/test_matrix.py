from project import matrix
from cfpq_data import labeled_two_cycles_graph
from pyformlang.cfg import CFG, Variable


def test_matrix():
    g = labeled_two_cycles_graph(2, 1, labels=("a", "b"))
    result = matrix.cfg_from_text_matrix(
        g,
        """
        S -> A B
        S -> A S1
        S1 -> S B
        A -> a
        B -> b
        """,
    )

    assert result == {
        (1, Variable("A"), 2),
        (2, Variable("A"), 0),
        (0, Variable("A"), 1),
        (3, Variable("B"), 0),
        (0, Variable("B"), 3),
        (0, Variable("S1"), 3),
        (2, Variable("S"), 3),
        (2, Variable("S1"), 0),
        (1, Variable("S"), 0),
        (1, Variable("S1"), 3),
        (0, Variable("S"), 3),
        (0, Variable("S1"), 0),
        (2, Variable("S"), 0),
        (2, Variable("S1"), 3),
        (1, Variable("S"), 3),
        (1, Variable("S1"), 0),
        (0, Variable("S"), 0),
    }


def test_matrix_sf():
    g = labeled_two_cycles_graph(2, 1, labels=("a", "b"))

    cfg = CFG.from_text(
        """
        S -> A B
        S -> A S1
        S1 -> S B
        A -> a
        B -> b
        """
    )

    result = matrix.query_graph_matrix(
        g, cfg, [0, 1, 2, 3], [0, 1, 2, 3], Variable("S")
    )
    assert result == {
        0: {0, 3},
        1: {0, 3},
        2: {0, 3},
        3: set(),
    }
