import sys
from antlr4 import *
from project.language.DOTBuilder import DOTBuilder
import pydot

from project.language.Executor import Executor
from project.language.Type import ParseTypeError
from project.language.Typer import Typer
from project.language.antlr_out.LanguageLexer import LanguageLexer
from project.language.antlr_out.LanguageParser import LanguageParser


def main(argv):
    if len(argv) != 2:
        print("Supply filename as an argument")

    with open(argv[1]) as f:
        stream = InputStream(f.read())

    lexer = LanguageLexer(stream)
    token_stream = CommonTokenStream(lexer)

    parser = LanguageParser(token_stream)
    walker = ParseTreeWalker()

    typer = Typer()
    program_tree = parser.program()

    try:
        walker.walk(typer, program_tree)
    except ParseTypeError as e:
        print("Type error occurred", file=sys.stderr)
        print(e.value, file=sys.stderr)

    try:
        executor = Executor(typer.variableTypes, typer.typeAnnotations)
        executor.visit(program_tree)
    except RuntimeError as e:
        print("Error occurred during execution", file=sys.stderr)
        print(e, file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv)
