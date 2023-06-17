import sys
from antlr4 import *
from project.language.DOTBuilder import DOTBuilder
import pydot


def main(argv):
    with open(argv[1], "r") as f:
        dot = DOTBuilder.build(f.read())
        dot.write_png(argv[2])


if __name__ == "__main__":
    main(sys.argv)
