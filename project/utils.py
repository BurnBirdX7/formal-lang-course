from typing import Tuple, Set

import cfpq_data as cfpq
import networkx as nt
import pydot

from collections import namedtuple

GraphData = namedtuple("GraphData", ["nodes_count", "edges_count", "labels"])


def get_graph_data_by_name(name: str) -> GraphData:
    """
    Return count of nodes, edges and list of labels of graph from CFPQ dataset
    """
    graph = get_graph_by_name(name)
    return get_graph_data(graph)


def get_graph_by_name(name: str) -> nt.classes.MultiDiGraph:
    """
    Returns graph from CFPQ dataset
    """
    path = cfpq.download(name)
    return cfpq.graph_from_csv(path)


def get_graph_data(graph: nt.classes.MultiDiGraph) -> GraphData:
    """
    Extracts graph info from the graph
    """
    return GraphData(
        graph.number_of_nodes(), graph.number_of_edges(), get_labels(graph)
    )


def get_labels(graph: nt.classes.MultiDiGraph) -> Set[str]:
    """
    Extracts set of labels from the graph
    """
    return set([label for (_, _, label) in graph.edges(data="label")])


def write_two_cycles_graph(
    n: int, m: int, labels: Tuple[str, str], path: str = "output.dot"
):
    """
    Generates graph that contains two cycles and writes it to the file
    :param n: nodes in 1st cycle
    :param m: nodes in 2nd cycle
    :param labels: tuple of labels: (1st cycle, 2nd cycle)
    :param path: path to the file to write the graph
    :return:
    """
    graph = cfpq.labeled_two_cycles_graph(n, m, labels=labels)
    graph_pd: pydot.Dot = nt.drawing.nx_pydot.to_pydot(graph)
    graph_pd.write_raw(path)
