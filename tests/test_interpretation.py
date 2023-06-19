import io
from typing import Tuple

import pytest

from project.language.interpret import *


def interpret(text: str) -> Tuple[str, str]:
    with io.StringIO() as out:
        with io.StringIO() as err:
            execute_code(text, out, err)
            return out.getvalue().strip(), err.getvalue().strip()


def test_int():
    text1 = """
    print 5;
    """
    text2 = """
    let a = 5;
    print 5;
    """

    expected = "5 :: IntType"

    for t in [text1, text2]:
        out, err = interpret(t)
        assert expected == out
        assert "" == err


@pytest.mark.parametrize(
    "intput",
    [
        """
    print {1, 2, 3, 4, 5};
    """,
        """
    let a = {1 .. 5};
    print a;
    """,
        """
    let a = {1, 3, 5, 2, 4};
    print a;
    """,
    ],
)
def test_set(intput):
    expected = "{ 1, 2, 3, 4, 5 } :: SetType<IntType>"
    out, err = interpret(intput)
    assert expected == out
    assert "" == err


@pytest.mark.parametrize(
    "intput",
    [
        """
    print [1, 2, 3];
    """,
        """
    let a = [1, 2, 3];
    print a;
    """,
    ],
)
def test_tyuple_iii(intput):
    expected = "[ 1, 2, 3 ] :: TupleType<IntType, IntType, IntType>"
    out, err = interpret(intput)
    assert expected == out
    assert "" == err


@pytest.mark.parametrize(
    "intput",
    [
        """
    print [1, 2, "Hello, world"];
    """,
        """
    let a = [1, 2, "Hello, world"];
    print a;
    """,
    ],
)
def test_tuple_iis(intput):
    expected = "[ 1, 2, Hello, world ] :: TupleType<IntType, IntType, StringType>"
    out, err = interpret(intput)
    assert expected == out
    assert "" == err


@pytest.mark.parametrize(
    "action, expected",
    [
        ("1 in s", "True"),
        ("2 in s", "True"),
        ("3 in s", "False"),
        ("1 in {1, 4}", "True"),
        ("2 in {1 .. 4}", "True"),
        ("3 in {1, 2, 4}", "False"),
    ],
)
def test_bool(action: str, expected: str):
    set_def = "let s = {1, 2};\n"
    prog = set_def + "print " + action + ";"
    print(prog)
    out, err = interpret(prog)
    assert out == expected + " :: BoolType"
    assert err == ""


def test_inner_tuple():
    intput = """
    let a = [1, 2, [3, {4, 5}], {6 .. 10}];
    print a;
    """
    expected = (
        "[ 1, 2, [ 3, { 4, 5 } ], { 6, 7, 8, 9, 10 } ] :: "
        "TupleType<IntType, IntType, TupleType<IntType, SetType<IntType>>, SetType<IntType>>"
    )
    out, err = interpret(intput)
    assert "" == err
    assert expected == out


def test_tuple_noval():
    """
    Tuple literal cannot contain anything but values
    :return:
    """
    input = """
    let a = 5;
    let t = [1, 2, a];
    """
    expected = (
        "Type error occurred\n"
        "Error Node is detected, Typing and Execution is unavailable, a"
    )
    out, err = interpret(input)
    assert "" == out
    assert expected == err


@pytest.mark.parametrize(
    "action, expected",
    [
        ("get_starts of fa", "{ 0, 2 } :: SetType<IntType>"),
        ("get_finals of fa", "{ 1, 3 } :: SetType<IntType>"),
        ("get_vertices of fa", "{ 0, 1, 2, 3 } :: SetType<IntType>"),
        ("get_labels of fa", "{ l2, l1 } :: SetType<StringType>"),
    ],
)
def test_simple_fa(action: str, expected: str):
    fa_def = 'let fa = "l1" | "l2";\n'
    prog = fa_def + "print " + action + ";"
    print(prog)
    out, err = interpret(prog)
    assert err == ""
    assert out == expected
