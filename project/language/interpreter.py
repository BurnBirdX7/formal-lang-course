import sys
from typing import Dict, Any, List, Set, Tuple

from antlr4 import *
from project.language.DOTBuilder import get_parser
from project.language.antlr_out.LanguageListener import LanguageListener
from project.language.antlr_out.LanguageParser import LanguageParser
from project.language.Type import *


def parse_program(prog: str):
    walker = ParseTreeWalker()
    ex = Executor()
    parser = get_parser(prog)

    if parser.getNumberOfSyntaxErrors() > 0:
        print("Syntax errors were found", file=sys.stderr)
        return

    try:
        walker.walk(ex, parser.program())
    except ParseTypeError as err:
        print("Error occurred", file=sys.stderr)
        print(err.value, file=sys.stderr)


class Executor(LanguageListener):
    def __init__(self):
        self.typeAnnotations: Dict[ParserRuleContext, Type] = {}
        self.valueAnnotations: Dict[ParserRuleContext, Any] = {}

        self.variableTypes: Dict[str, Type] = {}
        self.variableValues: Dict[str, Any] = {}

    def exitPrint(self, ctx: LanguageParser.PrintContext):
        self.valueAnnotations[ctx] = None
        self.typeAnnotations[ctx] = NoneType()

        val = self.valueAnnotations[ctx.expr()]
        typ = self.typeAnnotations[ctx.expr()]
        print(f"{val}   :: {typ}")

    def exitBind(self, ctx: LanguageParser.BindContext):
        self.valueAnnotations[ctx] = None
        self.typeAnnotations[ctx] = NoneType()

        patternCtx = ctx.pattern()
        patternType = self.typeAnnotations.get(patternCtx)
        patternName = self.valueAnnotations.get(patternCtx)

        exprCtx = ctx.expr()
        exprType = self.typeAnnotations.get(exprCtx)
        exprValue = self.valueAnnotations.get(exprCtx)

        self.bindToValue(patternName, patternType, exprValue, exprType)

    def bindToValue(
        self, patternName: str, patternType: Type, exprValue: Any, exprType: Type
    ):
        if patternType == VarType():
            self.variableValues[patternName] = exprValue
            self.variableTypes[patternName] = exprType
            return
        elif type(patternType) != PatternType:
            raise ParseTypeError(f"Unexpected pattern type: {patternType}")

        if type(exprType) == TypedSetType:
            self.bindToSet(patternType, exprValue, exprType)  # type: ignore
        elif type(exprType) == TupleType:
            self.bindToTuple(patternType, exprValue, exprType)  # type: ignore
        else:
            raise ParseTypeError(
                f"Binding {patternType} to {exprValue}::{exprType} is impossible"
            )

    def bindToSet(self, pattern: PatternType, setVal: Set[Any], setType: TypedSetType):
        error_template = f"Binding {pattern} to {setVal}::{setType}: "

        if len(pattern) != len(setVal):
            raise ParseTypeError(
                f"{error_template}pattern length and set length must be equal"
            )

        firstType = pattern.description[0]
        for typ in pattern.description[1:]:
            if typ != firstType:
                raise ParseTypeError(f"{error_template}pattern must be uniform")

        if firstType != VarType() and type(firstType) != PatternType:
            raise ParseTypeError(
                f"{error_template}:incompatible types: {firstType} and {setType.elementType}"
            )

        for subpatName, subpatType, exprVal in zip(
            pattern.names, pattern.description, setVal
        ):
            self.bindToValue(subpatName, subpatType, exprVal, setType.elementType)

    def bindToTuple(
        self, pattern: PatternType, tupleVal: Tuple[Any], tupleType: TupleType
    ):
        error_template = f"Binding {pattern} to {tupleVal}::{tupleType}: "

        if len(pattern) != len(tupleType):
            raise ParseTypeError(
                f"{error_template}pattern and tuple must be the same length"
            )

        for subpatName, subpatType, val, typ in zip(
            pattern.names, pattern.description, tupleVal, tupleType.description
        ):
            self.bindToValue(subpatName, subpatType, val, typ)

    # Patterns
    def exitPatternVar(self, ctx: LanguageParser.PatternVarContext):
        self.valueAnnotations[ctx] = ctx.VAR().getText()
        self.typeAnnotations[ctx] = VarType()

    def exitPatternPattern(self, ctx: LanguageParser.PatternPatternContext):
        def get_type(patternCtx):
            return self.typeAnnotations.get(patternCtx)

        def get_name(patternCtx: LanguageParser.PatternContext):
            typeType = type(self.typeAnnotations.get(patternCtx))
            if typeType == VarType or typeType == PatternType:
                return self.valueAnnotations.get(patternCtx)
            raise ParseTypeError(f"Unexpected type of the pattern: {typeType},")

        patternTypeList = list(map(get_type, ctx.pattern()))
        patternNameList = list(map(get_name, ctx.pattern()))
        self.typeAnnotations[ctx] = PatternType(patternTypeList, patternNameList)
        self.valueAnnotations[ctx] = "//pattern//"

    # Values
    def exitVal(self, ctx: LanguageParser.ValContext):
        # type
        if ctx.STRING():
            self.typeAnnotations[ctx] = StringType()
            self.valueAnnotations[ctx] = ctx.STRING().getText()
        elif ctx.INT():
            self.typeAnnotations[ctx] = IntType()
            self.valueAnnotations[ctx] = int(ctx.INT().getText())
        elif ctx.intSet():
            self.typeAnnotations[ctx] = TypedSetType(IntType())
            self.valueAnnotations[ctx] = self.valueAnnotations.get(ctx.intSet())

    # Set parsing, only values
    def exitSetEmpty(self, ctx: LanguageParser.SetEmptyContext):
        self.valueAnnotations[ctx] = set()

    def exitSetList(self, ctx: LanguageParser.SetListContext):
        intSet = set()
        for i in ctx.INT():
            intSet.add(int(i.getText()))
        self.valueAnnotations[ctx] = intSet

    def exitSetRange(self, ctx: LanguageParser.SetRangeContext):
        intSet = set()
        start, end = ctx.INT()
        start = int(start.getText())
        end = int(end.getText())
        intSet = set(range(start, end + 1))
        self.valueAnnotations[ctx] = intSet

    # Expression parsing
    def proxy_ctx(self, ctx, otherCtx):
        self.typeAnnotations[ctx] = self.typeAnnotations.get(otherCtx)
        self.valueAnnotations[ctx] = self.valueAnnotations.get(otherCtx)

    def exitExprVar(self, ctx: LanguageParser.ExprVarContext):
        varName = ctx.VAR().getText()
        self.typeAnnotations[ctx] = self.variableTypes.get(varName)
        self.valueAnnotations[ctx] = self.variableValues.get(varName)

    def exitExprVal(self, ctx: LanguageParser.ExprValContext):
        self.proxy_ctx(ctx, ctx.val())

    def visitErrorNode(self, node: ErrorNode):
        super().visitErrorNode(node)
        raise ParseTypeError(
            "Error Node is detected, Typing and Execution is unavailable"
        )
