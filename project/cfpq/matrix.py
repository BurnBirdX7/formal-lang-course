from typing import AbstractSet, Iterable, Set, Tuple, Dict

import networkx as nt
from pyformlang.cfg import CFG, Terminal, Epsilon, Variable
from project.wcnf import cfg_to_wcnf
from scipy.sparse import dok_matrix


def matrix_alg(
    graph: nt.MultiDiGraph,
    cfg: CFG,
) -> Set[Tuple]:
    """
    This function searches the graph and identifies all vertex pairs where the first vertex can be
    reached from the second vertex via a path that belongs to the given context-free grammar,
    without considering the starting non-terminal.
    :returns: Set of tuples (v1, nonterminal, v2), which describe edges (from, label, to)
    """
    cfg = cfg_to_wcnf(cfg)

    def get_nonterms(cfg: CFG) -> AbstractSet[Variable]:
        return {var for var in cfg.variables if var not in cfg.terminals}

    n = graph.number_of_nodes()
    T = {nt: dok_matrix((n, n), dtype=bool) for nt in get_nonterms(cfg)}
    for i, j, x in graph.edges(data="label"):
        for production in cfg.productions:
            t = production.body[0]
            if isinstance(t, Epsilon):
                T[production.head][i, j] = True
            if isinstance(t, Terminal) and t.value == x:
                T[production.head][i, j] = True
    T_prev = T
    while True:
        T = T.copy()
        for production in cfg.productions:
            if not isinstance(production.body[0], (Epsilon, Terminal)):
                T[production.head] += T[production.body[0]] @ T[production.body[1]]
        if all((T[key] != T_prev[key]).nnz == 0 for key in T.keys() | T_prev.keys()):
            break
        T_prev = T
    result = {
        (i, nt, j)
        for nt, matrix in T.items()
        for (i, j), value in matrix.todok().items()
        if value
    }
    return result


def query_graph_matrix(
    graph: nt.MultiDiGraph,
    cfg: CFG,
    start_vertices: Iterable[int],
    final_vertices: Iterable[int],
    start_nonterminal: Variable,
) -> Dict[int, Set[int]]:
    """
    This function executes a query on a graph using the matrix algorithm
    :return: the dictionary that maps starting vertices to the corresponding reachable vertices
    """

    ans = {u: set() for u in start_vertices}
    hellings_res = matrix_alg(graph, cfg)
    for u, non, v in hellings_res:
        if non == start_nonterminal and u in start_vertices and v in final_vertices:
            ans[u].add(v)
    return ans


def cfg_from_text_matrix(graph: nt.MultiDiGraph, cfg_text: str) -> Set[Tuple]:
    """
    Execute the Hellings algorithm using the context-free grammar provided in the text
    """
    return matrix_alg(graph, CFG.from_text(cfg_text))


def cfg_from_file_matrix(graph: nt.MultiDiGraph, cfg_file: str) -> Set[Tuple]:
    """
    Execute the Hellings algorithm using the context-free grammar provided in the file
    """
    with open(cfg_file) as cfg_file:
        cfg_text = cfg_file.read()
        return cfg_from_text_matrix(graph, cfg_text)
