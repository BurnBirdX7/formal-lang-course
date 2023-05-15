from typing import Dict, Set
from project.ecfg import ECFG, ECFGProduction
from pyformlang.cfg import CFG, Variable
from pyformlang.regular_expression import Regex
import pytest


TEST_PARAM = [
    ("S -> epsilon", {ECFGProduction(Variable("S"), Regex("$"))}),
    ("S -> epsilon | a S b S", {ECFGProduction(Variable("S"), Regex("$ | a S b S"))}),
    (
        """
            S -> if E then E else E
            E -> true | false
            """,
        {
            ECFGProduction(Variable("S"), Regex("if E then E else E")),
            ECFGProduction(Variable("E"), Regex("true | false")),
        },
    ),
]

ECFG_INVALID = """
            S -> a
            S -> b -> c
            """

ECFG_TEXT_1 = """
              S -> a
              S -> b
              """

ECFG_TEXT_2 = """
              S -> a | b
              """

# @pytest.mark.parametrize("text, expected", TEST_PARAM)
# def test_ecfg_productions(text: str, expected: Set[ECFGProduction]):
#     ecfg = ECFG.from_text(text)
#     assert ecfg.productions == expected


@pytest.mark.parametrize("text, expected", TEST_PARAM)
def test_production_equality(text: str, expected: Set[ECFGProduction]):
    ecfg = ECFG.from_cfg(CFG.from_text(text))

    for actual_prod in ecfg.productions:
        found = None
        for expected_prod in expected:
            if actual_prod == expected_prod:
                found = expected_prod
                break
        assert found is not None

    assert len(ecfg.productions) == len(expected)


def test_productions_invalid():
    with pytest.raises(RuntimeError):
        ECFG.from_text(ECFG_INVALID)


def test_text_equality():
    ecfg1 = ECFG.from_text(ECFG_TEXT_1)
    ecfg2 = ECFG.from_text(ECFG_TEXT_2)

    assert ecfg1 == ecfg2
