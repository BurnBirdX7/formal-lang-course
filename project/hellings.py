import networkx as nt
from pyformlang.cfg import CFG, Variable
from pyformlang.cfg.terminal import Terminal
from project.wcnf import cfg_to_wcnf

from typing import Set, Tuple, Dict, Iterable


def hellings(graph: nt.MultiDiGraph, cfg: CFG) -> Set[Tuple[int, int, int]]:
    """
    Hellings algorithm to discover paths with the given parameters
    :param graph: the graph to be searched
    :param cfg: the context-free grammat
    :return: Set of tuples (v1, nonterminal, v2), which describe edges (from, label, to)
    """

    wcnf = cfg_to_wcnf(cfg)
    eps_head = {prod.head.value for prod in wcnf.productions if not prod.body}
    term_head = {prod for prod in wcnf.productions if len(prod.body) == 1}
    nonterm_head = {prod for prod in wcnf.productions if len(prod.body) == 2}

    epsilon_edges = set()

    for h in eps_head:
        for v in range(graph.number_of_nodes()):
            epsilon_edges.add((v, h, v))

    terminal_edges = set()

    for u, v, e_data in graph.edges(data=True):
        for p in term_head:
            if p.body[0] == Terminal(e_data["label"]):
                terminal_edges.add((u, p.head.value, v))

    rules = epsilon_edges.union(terminal_edges)

    rules_copy = rules.copy()

    # Add edges created with multiple rules
    while rules_copy:
        u, A, v = rules_copy.pop()
        step = set()

        for frm, B, to in rules:
            if to == u:
                new_edges = set()
                for p in nonterm_head:
                    if (
                        p.body[0].value == B
                        and p.body[1].value == A
                        and (frm, p.head.value, v) not in rules
                    ):
                        new_edges.add((frm, p.head.value, v))
                step |= new_edges

        rules |= step
        rules_copy |= step
        step.clear()

        for frm, B, to in rules:
            if frm == v:
                new_edges = set()
                for p in nonterm_head:
                    if (
                        p.body[0].value == A
                        and p.body[1].value == B
                        and (u, p.head.value, to) not in rules
                    ):
                        new_edges.add((u, p.head.value, to))
                step |= new_edges

        rules |= step
        rules_copy |= step

    return rules


def query_graph(
    graph: nt.MultiDiGraph,
    cfg: CFG,
    start_vertices: Iterable[int],
    final_vertices: Iterable[int],
    start_nonterminal: Variable,
) -> Dict[int, Set[int]]:
    """
    This function executes a query on a graph using the Hellings algorithm
    :return: the dictionary that maps starting vertices to the corresponding reachable vertices
    """

    ans = {u: set() for u in start_vertices}
    hellings_res = hellings(graph, cfg)
    for u, non, v in hellings_res:
        if non == start_nonterminal and u in start_vertices and v in final_vertices:
            ans[u].add(v)
    return ans


def cfg_from_text_hellings(graph: nt.MultiDiGraph, cfg_text: str) -> Set[Tuple]:
    """
    Execute the Hellings algorithm using the context-free grammar provided in the text
    """
    return hellings(graph, CFG.from_text(cfg_text))


def cfg_from_file_hellings(graph: nt.MultiDiGraph, cfg_file: str) -> Set[Tuple]:
    """
    Execute the Hellings algorithm using the context-free grammar provided in the file
    """
    with open(cfg_file) as cfg_file:
        cfg_text = cfg_file.read()
        return cfg_from_text_hellings(graph, cfg_text)
