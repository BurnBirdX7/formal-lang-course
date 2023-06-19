import sys

from project.language.Executor import *
from project.language.interpret import *

from antlr4 import *


def online():
    typer = Typer()
    executor = Executor(typer.variableTypes, typer.typeAnnotations, sys.stdout)
    walker = ParseTreeWalker()

    print("Hello! Input 'q' to exit")

    while True:
        prog = input(" >>> ")
        if prog == "q":
            break

        if not does_belong_to_language(prog):
            print("Wrong syntax")
            continue

        tree = get_parser(prog)
        program_tree = tree.program()

        try:
            walker.walk(typer, program_tree)
        except ParseTypeError as e:
            print("Type Error", file=sys.stderr)
            print(e.value, file=sys.stderr)
            continue

        try:
            executor.visit(program_tree)
        except ExecutionError as e:
            print("Execution error", file=sys.stderr)
            print(e.value, file=sys.stderr)


def main(argv):
    if len(argv) != 2:
        try:
            online()
        except Exception as e:
            print(f"Internal error occurred, stopping...")
            print(e)
        return

    with open(argv[1], "r", encoding="utf-8") as f:
        prog = f.read()
    execute_code(prog, sys.stdout, sys.stderr)


if __name__ == "__main__":
    main(sys.argv)
