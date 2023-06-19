import sys
from typing import Dict

import networkx as nx
from antlr4 import *

from project.automata import (
    get_nfa_from_graph,
    nfa_production,
    nfa_reachable,
    nfa_union,
    nfa_from_string,
    nfa_concat,
    nfa_closure,
)

from project.language.antlr_out.LanguageVisitor import LanguageVisitor
from project.language.antlr_out.LanguageParser import LanguageParser
from project.language.Type import *

from project.language.Typer import Typer
from project.language.DOTBuilder import get_parser


class ExecutionError(RuntimeError):
    def __init__(self, msg: str):
        super().__init__(msg)
        self.value = msg


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
        typ = self.typeAnnotations.get(tree)
        if (
            not isinstance(tree, TerminalNode)
            and typ is not None
            and not typ.is_type(result)
        ):
            raise ExecutionError(
                "Expression value has incorrect type.\n"
                f"Expected type: {typ}\n"
                f"Expression value: {result} [py-type {type(result)}]"
            )
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
            raise ExecutionError("Unreachable code")
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
        fa1Packed, fa2Packed = self.visitChildren(ctx)

        if type(fa1Packed) == str and type(fa2Packed) == str:
            return fa1Packed + fa2Packed

        f1, f2 = Executor.get_2_nfas(fa1Packed, fa2Packed)

        return nfa_union(f1, f2)

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
        packedVal = self.visitChildren(ctx)
        return SetValue(nfa_reachable(packedVal.value))

    def visitExprLoad(self, ctx: LanguageParser.ExprLoadContext):
        if ctx.VAR():
            file = self.variableValues.get(ctx.VAR().getText())
        elif ctx.val():
            file = self.visit(ctx.val())
        else:
            raise ExecutionError("Unreachable code")

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

    @staticmethod
    def get_2_nfas(self, fa1Packed: FAValue | str, fa2Packed: FAValue | str):
        if type(fa1Packed) == FAValue and type(fa2Packed) == FAValue:
            f1 = fa1Packed.value
            f2 = fa2Packed.value
        elif type(fa1Packed) == FAValue and type(fa2Packed) == str:
            f1 = fa1Packed.value
            f2 = nfa_from_string(fa2Packed)
        elif type(fa1Packed) == str and type(fa2Packed) == FAValue:
            f1 = nfa_from_string(fa1Packed)
            f2 = fa2Packed.value
        return f1, f2

    def visitExprConcat(self, ctx: LanguageParser.ExprConcatContext):
        fa1Packed, fa2Packed = self.visitChildren(ctx)

        if fa1Packed == StringType() and fa2Packed == StringType():
            return fa1Packed + fa2Packed

        f1, f2 = Executor.get_2_nfas(fa1Packed, fa2Packed)

        return FAValue(nfa_concat(f1, f2))

    def visitExprKleene(self, ctx: LanguageParser.ExprKleeneContext):
        fa = self.visitChildren(ctx)
        return FAValue(nfa_closure(fa))

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
        fa1Packed, fa2Packed = self.visitChildren(ctx)
        return FAValue(nfa_production(fa1Packed.value, fa2Packed.value))
