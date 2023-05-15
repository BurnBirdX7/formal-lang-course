import itertools
import pytest
from project.language.language import *


valid = [
    # let:
    'let hello = "world!";',
    "let x = 1;",
    "let x = -1;",  # test negative integers
    "let x = {1..10};",
    "let x = {1, 2, 3, 4};",
    # comments:
    "// hello!!!",
    "// world!",
    "let x = 1; // comment",
    # print:
    "print {};",
    "print {-8..35};",
    "print {1, 2, 3, -6};",
    'print load "graph";',
    # map
    "print map g with \\a -> a in s;",
    "print map g with \\[a, b, c] -> b in g';",
    "print map (g) with \\[abc, d] -> abc in d;",
    # filter
    "print filter g with \\a -> a in s;",
    "print filter g with \\[a, b, c] -> b in g';",
    "print filter (g) with \\[abc, d] -> abc in d;",
]

invalid = [
    'let hello = abc";',  # no opening quote
    'let hello = "abc;',  # no closing quote
    'let hello = "abc"',  # no semicolon
    "print filter g with (\\a -> a);",  # lambdas cant be in parentheses
    # let:
    "let = 123;",
    "let a = ;",
    "let =;",
    "let a = 1 // commented ;",
    "let b = 2 // forgotten semicolon",
    # print:
    "print;",
    "print ;",
    'print "hello" // world',  # forgotten ;
]


@pytest.mark.parametrize(
    "prog, belongs",
    [(prog, True) for prog in valid] + [(prog, False) for prog in invalid],
)
def test_belongs_to_lang(prog: str, belongs: bool):
    assert belongs == does_belong_to_language(prog)


@pytest.mark.parametrize("combination", itertools.combinations(valid, 2))
def test_valid_combinations(combination):
    assert does_belong_to_language("".join(combination))
    assert does_belong_to_language(" ".join(combination))
    assert does_belong_to_language("\n".join(combination))
