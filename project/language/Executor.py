import networkx as nx
from antlr4 import *

from project.automata import *

from project.language.antlr_out.LanguageVisitor import LanguageVisitor
from project.language.antlr_out.LanguageParser import LanguageParser
from project.language.Type import *


class ExecutionError(RuntimeError):
    def __init__(self, msg: str):
        super().__init__(msg)
        self.value = msg


class Executor(LanguageVisitor):
    def __init__(
        self,
        variable_types: Dict[str, Type],
        type_annotations: Dict[ParserRuleContext, Type],
        file_out,
    ):
        self.variableTypes: Dict[str, Type] = variable_types
        self.variableValues: Dict[str, Any] = {}
        self.typeAnnotations: Dict[ParserRuleContext, Type] = type_annotations
        self.valueAnnotations: Dict[ParserRuleContext, Any] = {}
        self.fileOut = file_out

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

    def unbind(self, pattern: Union[VarType, PatternType]):
        if type(pattern) == VarType:
            self.variableValues.pop(pattern.name)
            self.variableTypes.pop(pattern.name)
        else:
            for subpattern in pattern.description:
                self.unbind(subpattern)

    def bindType(
        self, pattern: Union[VarType, PatternType], value: Union[Type, TupleType]
    ):
        if type(pattern) == VarType:
            self.bindTypeToVar(pattern, value)
        else:
            self.bindTupleToPattern(pattern, value)

    def bindTypeToVar(self, var: VarType, varType: Type):
        self.variableTypes[var.name] = varType

    def bindTupleToPattern(self, pattern: PatternType, tupleType: TupleType):
        for subpattern, val in zip(pattern.description, tupleType.description):
            self.bindType(subpattern, tupleType)

    def bindValue(self, pattern: Union[VarType, PatternType], value: Any):
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
        pattern: Union[VarType, PatternType] = self.typeAnnotations.get(ctx.pattern())  # type: ignore
        expr = self.valueAnnotations.get(ctx.expr())
        self.valueAnnotations[ctx.pattern()] = expr
        self.bindValue(pattern, expr)

    def visitPrint(self, ctx: LanguageParser.PrintContext):
        self.visitChildren(ctx)
        val = self.valueAnnotations.get(ctx.expr())
        typ = self.typeAnnotations.get(ctx.expr())

        if val is None:
            print(f"<None> :: {typ}", file=self.fileOut)
        else:
            print(f"{val!s} :: {typ!s}", file=self.fileOut)

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

    @staticmethod
    def underlying_values(states: Iterable[State]) -> Set:
        return set(map(lambda s: s.value, states))

    def visitExprGetStarts(self, ctx: LanguageParser.ExprGetStartsContext):
        faPacked = self.visitChildren(ctx)
        fa: EpsilonNFA = faPacked.value
        return SetValue(self.underlying_values(fa.start_states))

    def visitExprTransition(self, ctx: LanguageParser.ExprTransitionContext):
        return super().visitExprTransition(ctx)

    def visitExprAddFinals(self, ctx: LanguageParser.ExprAddFinalsContext):
        faPacked, startsPacked = self.visitChildren(ctx)
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
        exprVal: Union[TupleValue, SetValue] = self.visit(ctx.expr())
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

        if type(fa1Packed) == SetValue and type(fa2Packed) == SetValue:
            return SetValue(fa1Packed.value.union(fa2Packed.value))

        f1, f2 = Executor.get_2_nfas(fa1Packed, fa2Packed)

        return FAValue(nfa_union(f1, f2))

    def visitExprSetFinals(self, ctx: LanguageParser.ExprSetFinalsContext):
        faPacked, startsPacked = self.visitChildren(ctx)
        fa: EpsilonNFA = faPacked.value.copy()
        for state in faPacked.value.final_states:
            fa.remove_final_state(state)
        for state in startsPacked.value:
            fa.add_final_state(state)
        return FAValue(fa)

    def visitExprAddStarts(self, ctx: LanguageParser.ExprAddStartsContext):
        faPacked, startsPacked = self.visitChildren(ctx)
        fa: EpsilonNFA = faPacked.value.copy()
        for state in startsPacked.value:
            fa.add_start_state(state)
        return FAValue(fa)

    def visitExprGetVertices(self, ctx: LanguageParser.ExprGetVerticesContext):
        faPacked = self.visitChildren(ctx)
        fa: EpsilonNFA = faPacked.value
        return SetValue(self.underlying_values(fa.states))

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
        reachable = nfa_reachable(packedVal.value)
        reachable_tuples = map(lambda elem: TupleValue(elem), reachable)
        return SetValue(set(reachable_tuples))

    def visitExprLoad(self, ctx: LanguageParser.ExprLoadContext):
        if ctx.VAR():
            file = self.variableValues.get(ctx.VAR().getText())
        elif ctx.val():
            file = self.visit(ctx.val())
        else:
            raise ExecutionError("Unreachable code")

        graph = nx.nx_pydot.read_dot(file)
        file_fa = get_nfa_from_graph(graph, graph.nodes, graph.nodes)

        fa = EpsilonNFA()  # Convert States to int

        def convert(state: State) -> State:
            return State(int(state.value))

        try:
            for u, l, v in file_fa:
                fa.add_transition(convert(u), l, convert(v))

            for s in file_fa.start_states:
                fa.add_start_state(convert(s))

            for s in file_fa.final_states:
                fa.add_final_state(convert(s))
        except TypeError:
            raise ExecutionError(
                f"{ctx.getText()}: Vertices of a graph must be convertable to int to be loaded"
            )

        return FAValue(fa)

    def visitExprGetFinals(self, ctx: LanguageParser.ExprGetFinalsContext):
        faPacked = self.visitChildren(ctx)
        fa: EpsilonNFA = faPacked.value
        return SetValue(self.underlying_values(fa.final_states))

    def visitExprGetLabels(self, ctx: LanguageParser.ExprGetLabelsContext):
        faPacked = super().visitExprGetEdges(ctx)
        fa: EpsilonNFA = faPacked.value
        labelSet = set()
        for u, label, v in fa:
            labelSet.add(label.value)
        return SetValue(labelSet)

    def visitExprIn(self, ctx: LanguageParser.ExprInContext):
        val, cont = self.visitChildren(ctx)
        return val in cont.value

    @staticmethod
    def get_2_nfas(fa1Packed: Union[FAValue, str], fa2Packed: Union[FAValue, str]):
        if type(fa1Packed) == FAValue:
            f1 = fa1Packed.value
        else:
            f1 = nfa_from_string(fa1Packed)
        if type(fa2Packed) == FAValue:
            f2 = fa2Packed.value
        else:
            f2 = nfa_from_string(fa2Packed)
        return f1, f2

    def visitExprConcat(self, ctx: LanguageParser.ExprConcatContext):
        fa1Packed, fa2Packed = self.visitChildren(ctx)
        if type(fa1Packed) == str and type(fa2Packed) == str:
            return fa1Packed + fa2Packed

        f1, f2 = Executor.get_2_nfas(fa1Packed, fa2Packed)
        return FAValue(nfa_concat(f1, f2))

    def visitExprKleene(self, ctx: LanguageParser.ExprKleeneContext):
        fa = self.visitChildren(ctx)
        return FAValue(nfa_closure(fa.value))

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
        exprVal: Union[TupleValue, SetValue] = self.visit(ctx.expr())
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
