import sys

from project.language.interpret import execute_code


def main(argv):
    if len(argv) != 2:
        print("Supply filename as an argument")

    with open(argv[1], "r", encoding="utf-8") as f:
        prog = f.read()

    execute_code(prog, sys.stdout, sys.stderr)


if __name__ == "__main__":
    main(sys.argv)
