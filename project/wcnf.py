from typing import AbstractSet

from pyformlang import cfg  # type: ignore


def load_cfg(name: str) -> cfg.CFG:
    """
    Loads CFG from file
    :param name: name of file
    :return: CFG instance
    """
    with open(name, "r") as file:
        return cfg.CFG.from_text(file.read())


def save_cfg(name: str, g: cfg.CFG) -> None:
    """
    Saves CFG into a file
    :param name: file name
    :param g: CFG instance
    """
    with open(name, "w") as file:
        file.write(g.to_text())


def cfg_to_wcnf(g: cfg.CFG) -> cfg.CFG:
    """
    Transforms grammar into WCNF

    Gets productions like *non-terminal* -> eps (1)
    Gets prodcutions like A -> *start_symbol*   (2)
    Gets CGF in CNF

    Constructs new CFG by adding productions of CNF with (1) and (2)

    :param g: grammar
    :return: grammar in WCNF
    """

    new_cfg = g.eliminate_unit_productions().remove_useless_symbols()
    prods = new_cfg._decompose_productions(
        new_cfg._get_productions_with_only_single_terminals()
    )

    return cfg.CFG(start_symbol=new_cfg.start_symbol, productions=prods)
