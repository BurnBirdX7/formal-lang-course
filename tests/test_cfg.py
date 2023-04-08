import pytest  # type: ignore
from typing import List, Tuple

from project import wcnf


def file(name: str) -> str:
    return f"tests/cfgs/{name}.txt"


def files(file_list: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    return [(file(a), file(b)) for a, b in file_list]


@pytest.mark.parametrize(
    "inp, exp",
    files(
        [
            ("input0", "expected0"),
            ("input1", "expected1"),
            ("input2", "expected2"),
            ("input3", "expected3"),
        ]
    ),
)
def test_wcfg(inp, exp):
    weak = wcnf.cfg_to_wcnf(wcnf.load_cfg(inp))
    expected = wcnf.load_cfg(exp)
    assert set(weak.productions) == set(expected.productions)
