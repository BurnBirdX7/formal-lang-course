from typing import Tuple, Set

import cfpq_data as cfpq
import networkx as nt
import pydot

from collections import namedtuple

GraphData = namedtuple("GraphData", ["nodes_count", "edges_count", "labels"])


def get_graph_data_by_name(name: str) -> GraphData:
    graph = get_graph_by_name(name)
    return get_graph_data(graph)


def get_graph_by_name(name: str) -> nt.classes.MultiDiGraph:
    path = cfpq.download(name)
    return cfpq.graph_from_csv(path)


def get_graph_data(graph: nt.classes.MultiDiGraph) -> GraphData:
    return GraphData(
        graph.number_of_nodes(), graph.number_of_edges(), get_labels(graph)
    )


def get_labels(graph: nt.classes.MultiDiGraph) -> Set[str]:
    return set([label for (_, _, label) in graph.edges(data="label")])


def write_two_cycles_graph(
    n: int, m: int, labels: Tuple[str, str], path: str = "output.dot"
):
    graph = cfpq.labeled_two_cycles_graph(n, m, labels=labels)
    graph_pd: pydot.Dot = nt.drawing.nx_pydot.to_pydot(graph)
    graph_pd.write_raw(path)
