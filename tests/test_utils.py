from project import utils
import pydot
import networkx as nt


def test_get_labels():
    dot = """
    digraph {
        a;
        b;
        c;
        a -> b [label=a]
        b -> c [label=b]
        c -> a [label=ouch]
    }
    """

    [graph_pd] = pydot.graph_from_dot_data(dot)
    graph = nt.drawing.nx_pydot.from_pydot(graph_pd)

    labels = {"a", "b", "ouch"}

    assert utils.get_labels(graph) == labels


def test_get_graph_data_by_name():
    vert, edges, labels = utils.get_graph_data_by_name("wc")

    assert vert == 332
    assert edges == 269
    assert labels == {"a", "d"}


def test_write_two_cycles_graph():
    NODES_A = 10
    NODES_B = 9
    LABELS = ("QWE", "RTY")
    PATH = "test.dot"

    utils.write_two_cycles_graph(NODES_A, NODES_B, LABELS, PATH)

    graph = nt.drawing.nx_pydot.read_dot(PATH)

    data = utils.get_graph_data(graph)
    m, n, labels = data

    print(f"{data=}")

    assert (
        n == NODES_A + NODES_B + 1 + 1
    )  # + 1 common node, + 1 to account for ghost "\\n" node
    assert m == n + 1 - 1  # + 1 because M = N + 1, - 1 to account for the ghost node
    assert labels == set(LABELS)

    # pyplot's Ghost node issue:
    # https://github.com/pydot/pydot/issues/280
