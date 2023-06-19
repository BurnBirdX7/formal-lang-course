from project.language.Executor import Executor, ExecutionError
from project.language.Type import ParseTypeError
from project.language.Typer import Typer

from project.language.antlr_out.LanguageParser import LanguageParser
from project.language.antlr_out.LanguageLexer import LanguageLexer

from antlr4 import *


def get_parser(prog: str) -> LanguageParser:
    """
    Creates Parser object for provided text
    :param prog:
    :return:
    """
    input_stream = InputStream(prog)
    lexer = LanguageLexer(input_stream)
    stream = CommonTokenStream(lexer)
    return LanguageParser(stream)


def does_belong_to_language(prog: str):
    """
    Checks if program belongs to the language
    :param prog: program to check
    :return: True if belongs, False otherwise
    """
    parser = get_parser(prog)
    parser.removeErrorListeners()
    parser.program()
    return parser.getNumberOfSyntaxErrors() == 0


def type_program(prog: str, file_out, file_err):
    """
    Accepts program as string, prints types of the variables to the file_out,
    and errors to the file_err
    :param prog: program
    :param file_out: standard output
    :param file_err: error channel
    """
    walker = ParseTreeWalker()
    typer = Typer()
    parser = get_parser(prog)

    if parser.getNumberOfSyntaxErrors() > 0:
        print("Syntax errors were found", file=file_err)
        return
    try:
        walker.walk(typer, parser.program())

        print("Variables:")
        for var, typ in typer.variableTypes.items():
            print(f"{var} :: {typ}", file=file_out)

    except ParseTypeError as err:
        print("Error occurred", file=file_err)
        print(err.value, file=file_err)


def execute_code(prog: str, file_out, file_err):
    """
    Executes program
    :param prog: text of the program
    :param file_out: standard output
    :param file_err: error channel
    """
    tree = get_parser(prog)
    walker = ParseTreeWalker()
    typer = Typer()
    program_tree = tree.program()

    try:
        walker.walk(typer, program_tree)
    except ParseTypeError as e:
        print("Type error occurred", file=file_err)
        print(e.value, file=file_err)

    try:
        executor = Executor(typer.variableTypes, typer.typeAnnotations, file_out)
        executor.visit(program_tree)
    except ExecutionError as e:
        print("Error occurred during execution", file=file_err)
        print(e.value, file=file_err)
