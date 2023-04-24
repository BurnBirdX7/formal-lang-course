import pytest

from project.hellings import *
from cfpq_data import labeled_cycle_graph, labeled_two_cycles_graph

prod1 = "S -> epsilon"
prod2 = "S -> a | b"
prod3 = """
            S -> A B
            S -> epsilon
            S -> S B
            A -> a
            B -> b
         """


@pytest.mark.parametrize(
    "cfg, graph, expected",
    [
        (prod1, labeled_cycle_graph(2, "a"), {(1, "S", 1), (0, "S", 0)}),
        (
            prod2,
            labeled_cycle_graph(4, "a"),
            {(1, "S", 2), (0, "S", 1), (3, "S", 0), (2, "S", 3)},
        ),
        (
            prod3,
            labeled_two_cycles_graph(2, 2, labels=("a", "b")),
            {
                (0, "A", 1),
                (0, "B", 3),
                (0, "S", 0),
                (0, "S", 3),
                (0, "S", 4),
                (1, "A", 2),
                (1, "S", 1),
                (2, "A", 0),
                (2, "S", 0),
                (2, "S", 2),
                (2, "S", 3),
                (2, "S", 4),
                (3, "B", 4),
                (3, "S", 0),
                (3, "S", 3),
                (3, "S", 4),
                (4, "B", 0),
                (4, "S", 0),
                (4, "S", 3),
                (4, "S", 4),
            },
        ),
    ],
)
def test_hellings(cfg, graph, expected):
    res = hellings(graph, CFG.from_text(cfg))
    assert res == expected


def test_query_to_cfg():
    cfg = prod3
    graph = labeled_two_cycles_graph(2, 2, labels=("a", "b"))
    expected = {0: {4}, 2: {2, 4}}
    assert (
        query_graph_hellings(graph, CFG.from_text(cfg), [0, 2], [2, 4], Variable("S"))
        == expected
    )
