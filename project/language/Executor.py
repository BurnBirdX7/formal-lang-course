import sys
from typing import Dict, Any, List, Set, Tuple, Optional, Iterable

import networkx as nx
from antlr4 import *
from pyformlang.finite_automaton import EpsilonNFA

from project.automata import get_nfa_from_graph

from project.language.antlr_out.LanguageVisitor import LanguageVisitor
from project.language.antlr_out.LanguageParser import LanguageParser
from project.language.Value import *
from project.language.Type import *

from project.language.Typer import Typer
from project.language.DOTBuilder import get_parser


def execute_code(prog):
    tree = get_parser(prog)
    walker = ParseTreeWalker()
    typer = Typer()
    program_tree = tree.program()

    try:
        walker.walk(typer, program_tree)
    except ParseTypeError as e:
        print("Type error occurred", file=sys.stderr)
        print(e.value, file=sys.stderr)

    executor = Executor(typer.variableTypes, typer.typeAnnotations)
    executor.visit(program_tree)


class Executor(LanguageVisitor):
    def __init__(
        self,
        variable_types: Dict[str, Type],
        type_annotations: Dict[ParserRuleContext, Type],
    ):
        self.variableTypes: Dict[str, Type] = variable_types
        self.variableValues: Dict[str, Any] = {}
        self.typeAnnotations: Dict[ParserRuleContext, Type] = type_annotations
        self.valueAnnotations: Dict[ParserRuleContext, Any] = {}

    def visitChildren(self, node):
        result = self.defaultResult()
        n = node.getChildCount()
        for i in range(n):
            if not self.shouldVisitNextChild(node, result):
                return result

            c = node.getChild(i)
            childResult = self.visit(c)  # difference in this line
            result = self.aggregateResult(result, childResult)

        return result

    def aggregateResult(self, aggregate, nextResult):
        if nextResult is None:
            return aggregate

        if aggregate is None:
            return nextResult
        if type(aggregate) == list:
            return aggregate + [nextResult]
        return [aggregate, nextResult]

    def visit(self, tree):
        result = tree.accept(self)
        self.valueAnnotations[tree] = result
        return result

    def visitProgram(self, ctx: LanguageParser.ProgramContext):
        return super().visitChildren(ctx)

    def unbind(self, pattern: VarType | PatternType):
        if type(pattern) == VarType:
            self.variableValues.pop(pattern.name)
            self.variableTypes.pop(pattern.name)
        else:
            for subpattern in pattern.description:
                self.unbind(subpattern)

    def bindType(self, pattern: VarType | PatternType, value: Type | TupleType):
        if type(pattern) == VarType:
            self.bindTypeToVar(pattern, value)
        else:
            self.bindTupleToPattern(pattern, value)

    def bindTypeToVar(self, var: VarType, varType: Type):
        self.variableTypes[var.name] = varType

    def bindTupleToPattern(self, pattern: PatternType, tupleType: TupleType):
        for subpattern, val in zip(pattern.description, tupleType.description):
            self.bindType(subpattern, tupleType)

    def bindValue(self, pattern: VarType | PatternType, value: Any):
        if type(pattern) == VarType:
            self.bindValueToVar(pattern, value)
        else:
            self.bindIterableValueToPattern(pattern, value)

    def bindValueToVar(self, var: VarType, value: Any):
        self.variableValues[var.name] = value

    def bindIterableValueToPattern(self, pattern: PatternType, value: Iterable[Any]):
        for subpattern, val in zip(pattern.description, value):
            self.bindValue(subpattern, value)

    def visitBind(self, ctx: LanguageParser.BindContext):
        self.visit(ctx.expr())  # we do not need to visit pattern
        pattern: VarType | PatternType = self.typeAnnotations.get(ctx.pattern())  # type: ignore
        expr = self.valueAnnotations.get(ctx.expr())
        self.valueAnnotations[ctx.pattern()] = expr
        self.bindValue(pattern, expr)

    def visitPrint(self, ctx: LanguageParser.PrintContext):
        self.visitChildren(ctx)
        val = self.valueAnnotations.get(ctx.expr())
        typ = self.typeAnnotations.get(ctx.expr())

        if val is None:
            print(f"<None> :: {typ}")
        else:
            print(f"{val!s} :: {typ!s}")

    def visitVal(self, ctx: LanguageParser.ValContext):
        self.visitChildren(ctx)
        if ctx.STRING():
            val = ctx.STRING().getText()[1:-1]  # remove quotes
        elif ctx.INT():
            val = int(ctx.INT().getText())
        elif ctx.tuple_():
            val = self.valueAnnotations.get(ctx.tuple_())
        elif ctx.intSet():
            val = self.valueAnnotations.get(ctx.intSet())
        else:
            raise RuntimeError("Unreachable")
        return val

    def visitSetEmpty(self, ctx: LanguageParser.SetEmptyContext):
        return SetValue(set())

    def visitSetList(self, ctx: LanguageParser.SetListContext):
        intSet: Set[int] = set()
        for lit in ctx.INT():
            intSet.add(int(lit.getText()))
        return SetValue(intSet)

    def visitSetRange(self, ctx: LanguageParser.SetRangeContext):
        start, end = ctx.INT()
        start = int(start.getText())
        end = int(end.getText())
        intSet = set(range(start, end + 1))
        return SetValue(intSet)

    def visitTuple(self, ctx: LanguageParser.TupleContext):
        self.visitChildren(ctx)
        tup = []  # Language's tuples represented by Python Lists
        for val in ctx.val():
            tup.append(self.valueAnnotations.get(val))

        return TupleValue(tup)

    def visitLambda(self, ctx: LanguageParser.LambdaContext):
        return  # Lambda has no value, only type

    def visitExprGetStarts(self, ctx: LanguageParser.ExprGetStartsContext):
        faPacked = self.visitChildren(ctx)
        fa: EpsilonNFA = faPacked.value
        return SetValue(fa.start_states)

    def visitExprTransition(self, ctx: LanguageParser.ExprTransitionContext):
        return super().visitExprTransition(ctx)

    def visitExprAddFinals(self, ctx: LanguageParser.ExprAddFinalsContext):
        faPacked, startsPacked = self.visitVal(ctx)
        fa: EpsilonNFA = faPacked.value.copy()
        for state in fa.final_states:
            fa.remove_final_state(state)
        for state in startsPacked.value:
            fa.add_final_state(state)
        return FAValue(fa)

    def visitExprVar(self, ctx: LanguageParser.ExprVarContext):
        return self.variableValues.get(ctx.VAR().getText())

    def visitExprFilter(self, ctx: LanguageParser.ExprFilterContext):
        lambda_: LambdaType = self.typeAnnotations.get(ctx.lambda_())
        exprVal: TupleValue | SetValue = self.visit(ctx.expr())
        resultSet = set()
        for elem in exprVal.value:
            self.bindValue(lambda_.pattern, elem)
            self.bindType(lambda_.pattern, lambda_.patternType)
            ret = self.visit(lambda_.body)
            self.unbind(lambda_.pattern)
            if ret:
                resultSet.add(elem)

        return SetValue(resultSet)

    def visitExprUnion(self, ctx: LanguageParser.ExprUnionContext):
        return super().visitExprUnion(ctx)

    def visitExprSetFinals(self, ctx: LanguageParser.ExprSetFinalsContext):
        faPacked, startsPacked = self.visitVal(ctx)
        fa: EpsilonNFA = faPacked.value.copy()
        for state in faPacked.value.final_states:
            fa.remove_final_state(state)
        for state in startsPacked.value:
            fa.add_final_state(state)
        return FAValue(fa)

    def visitExprAddStarts(self, ctx: LanguageParser.ExprAddStartsContext):
        faPacked, startsPacked = self.visitVal(ctx)
        fa: EpsilonNFA = faPacked.value.copy()
        for state in startsPacked.value:
            fa.add_start_state(state)
        return FAValue(fa)

    def visitExprGetVertices(self, ctx: LanguageParser.ExprGetVerticesContext):
        faPacked = self.visitChildren(ctx)
        fa: EpsilonNFA = faPacked.value
        return SetValue(fa.states)

    def visitExprBraced(self, ctx: LanguageParser.ExprBracedContext):
        return super().visitExprBraced(ctx)

    def visitExprGetEdges(self, ctx: LanguageParser.ExprGetEdgesContext):
        faPacked = super().visitExprGetEdges(ctx)
        fa: EpsilonNFA = faPacked.value
        edgeSet = set()
        for u, label, v in fa:
            edge = TupleValue([u, label, v])
            edgeSet.add(edge)
        return SetValue(edgeSet)

    def visitExprGetReachable(self, ctx: LanguageParser.ExprGetReachableContext):
        return super().visitExprGetReachable(ctx)

    def visitExprLoad(self, ctx: LanguageParser.ExprLoadContext):
        if ctx.VAR():
            file = self.variableValues.get(ctx.VAR().getText())
        elif ctx.val():
            file = self.visit(ctx.val())
        else:
            raise RuntimeError("Unreachable code")

        graph = nx.nx_pydot.read_dot(file)
        fa = get_nfa_from_graph(graph, graph.nodes, graph.nodes)
        return FAValue(fa)

    def visitExprGetFinals(self, ctx: LanguageParser.ExprGetFinalsContext):
        faPacked = self.visitChildren(ctx)
        fa: EpsilonNFA = faPacked.value
        return SetValue(fa.final_states)

    def visitExprGetLabels(self, ctx: LanguageParser.ExprGetLabelsContext):
        faPacked = super().visitExprGetEdges(ctx)
        fa: EpsilonNFA = faPacked.value
        labelSet = set()
        for u, label, v in fa:
            labelSet.add(label)
        return SetValue(labelSet)

    def visitExprIn(self, ctx: LanguageParser.ExprInContext):
        cont: TupleValue | SetValue
        val, cont = self.visitChildren(ctx)
        return val in cont.value

    def visitExprConcat(self, ctx: LanguageParser.ExprConcatContext):
        lhs, rhs = ctx.expr()
        lType = self.typeAnnotations.get(lhs)
        rType = self.typeAnnotations.get(rhs)

        if lType == StringType() and rType == StringType():
            lVal, rVal = self.visitChildren(ctx)
            return lVal + rVal

        raise RuntimeError("Unsupported yet")

    def visitExprKleene(self, ctx: LanguageParser.ExprKleeneContext):
        return super().visitExprKleene(ctx)

    def visitExprSetStarts(self, ctx: LanguageParser.ExprSetStartsContext):
        faPacked, startsPacked = self.visitChildren(ctx)
        fa: EpsilonNFA = faPacked.value.copy()
        for state in faPacked.value.start_states:
            fa.remove_start_state(state)
        for state in startsPacked.value:
            fa.add_start_state(state)
        return FAValue(fa)

    def visitExprMap(self, ctx: LanguageParser.ExprMapContext):
        lambda_: LambdaType = self.typeAnnotations.get(ctx.lambda_())
        exprVal: TupleValue | SetValue = self.visit(ctx.expr())
        resultSet = set()
        for elem in exprVal.value:
            self.bindValue(lambda_.pattern, elem)
            self.bindType(lambda_.pattern, lambda_.patternType)
            ret = self.visit(lambda_.body)
            self.unbind(lambda_.pattern)
            resultSet.add(ret)

        return SetValue(resultSet)

    def visitExprProduct(self, ctx: LanguageParser.ExprProductContext):
        return super().visitExprProduct(ctx)
