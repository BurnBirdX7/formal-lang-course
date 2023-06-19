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
        result = []
        n = node.getChildCount()
        for i in range(n):
            if not self.shouldVisitNextChild(node, result):
                return result

            c = node.getChild(i)
            childResult = self.visit(c)  # use visit instead of accept
            result = self.aggregateResult(result, childResult)

        if len(result) == 0:
            return None
        if len(result) == 1:
            return result[0]
        return result

    def aggregateResult(self, aggregate: List[Any], nextResult: Any) -> List[Any]:
        if nextResult is None:
            return aggregate

        aggregate.append(nextResult)
        return aggregate

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
                f"Expression value: {result} [type {type(result)}]"
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

        typ.print_value(val, self.fileOut)

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
        return set()

    def visitSetList(self, ctx: LanguageParser.SetListContext):
        intSet: Set[int] = set()
        for lit in ctx.INT():
            intSet.add(int(lit.getText()))
        return intSet

    def visitSetRange(self, ctx: LanguageParser.SetRangeContext):
        start, end = ctx.INT()
        start = int(start.getText())
        end = int(end.getText())
        intSet = set(range(start, end + 1))
        return intSet

    def visitTuple(self, ctx: LanguageParser.TupleContext):
        self.visitChildren(ctx)
        tup = []  # Language's tuples represented by Python Lists
        for val in ctx.val():
            tup.append(self.valueAnnotations.get(val))

        return tuple(tup)

    def visitLambda(self, ctx: LanguageParser.LambdaContext):
        return  # Lambda has no value, only type

    @staticmethod
    def underlying_values(states: Iterable[State]) -> Set:
        """
        Extracts inner values from Container of States
        :param states: any iterable of State
        :return: Set of their inner values
        """
        return set(map(lambda s: s.value, states))

    def visitExprGetStarts(self, ctx: LanguageParser.ExprGetStartsContext):
        fa: EpsilonNFA = self.visitChildren(ctx)
        return self.underlying_values(fa.start_states)

    def visitExprTransition(self, ctx: LanguageParser.ExprTransitionContext):
        return super().visitExprTransition(ctx)

    def visitExprAddFinals(self, ctx: LanguageParser.ExprAddFinalsContext):
        fa, starts = self.visitChildren(ctx)
        fa: EpsilonNFA = fa.copy()
        starts: set
        for state in fa.final_states:
            fa.remove_final_state(state)
        for state in starts:
            fa.add_final_state(state)
        return fa

    def visitExprVar(self, ctx: LanguageParser.ExprVarContext):
        return self.variableValues.get(ctx.VAR().getText())

    def visitExprFilter(self, ctx: LanguageParser.ExprFilterContext):
        lambda_: LambdaType = self.typeAnnotations.get(ctx.lambda_())
        exprVal: Union[tuple, set] = self.visit(ctx.expr())
        resultSet = set()
        for elem in exprVal:
            self.bindValue(lambda_.pattern, elem)
            self.bindType(lambda_.pattern, lambda_.patternType)
            ret = self.visit(lambda_.body)
            self.unbind(lambda_.pattern)
            if ret:
                resultSet.add(elem)

        return resultSet

    def visitExprUnion(self, ctx: LanguageParser.ExprUnionContext):
        fa1, fa2 = self.visitChildren(ctx)

        if type(fa1) == set and type(fa2) == set:
            return fa1.union(fa2)

        f1, f2 = Executor.get_2_nfas(fa1, fa2)

        return nfa_union(f1, f2)

    def visitExprSetFinals(self, ctx: LanguageParser.ExprSetFinalsContext):
        fa_old, startsPacked = self.visitChildren(ctx)
        fa: EpsilonNFA = fa_old.copy()
        startsPacked: set
        for state in fa_old.final_states:
            fa.remove_final_state(state)
        for state in startsPacked:
            fa.add_final_state(state)
        return fa

    def visitExprAddStarts(self, ctx: LanguageParser.ExprAddStartsContext):
        fa_old, starts = self.visitChildren(ctx)
        fa: EpsilonNFA = fa_old.copy()
        for state in starts:
            fa.add_start_state(state)
        return fa

    def visitExprGetVertices(self, ctx: LanguageParser.ExprGetVerticesContext):
        faPacked = self.visitChildren(ctx)
        fa: EpsilonNFA = faPacked
        return self.underlying_values(fa.states)

    def visitExprGetEdges(self, ctx: LanguageParser.ExprGetEdgesContext):
        fa = self.visitChildren(ctx)
        fa: EpsilonNFA
        edgeSet = set()
        for u, label, v in fa:
            edge = (u.value, label.value, v.value)
            edgeSet.add(edge)
        return edgeSet

    def visitExprGetReachable(self, ctx: LanguageParser.ExprGetReachableContext):
        val = self.visitChildren(ctx)
        return nfa_reachable(val)

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

        return fa

    def visitExprGetFinals(self, ctx: LanguageParser.ExprGetFinalsContext):
        fa = self.visitChildren(ctx)
        fa: EpsilonNFA
        return self.underlying_values(fa.final_states)

    def visitExprGetLabels(self, ctx: LanguageParser.ExprGetLabelsContext):
        fa = self.visitChildren(ctx)
        fa: EpsilonNFA
        labelSet = set()
        for u, symbol, v in fa:
            labelSet.add(symbol.value)
        return labelSet

    def visitExprIn(self, ctx: LanguageParser.ExprInContext):
        val, cont = self.visitChildren(ctx)
        val: Any
        cont: Iterable[Any]
        return val in cont

    @staticmethod
    def get_2_nfas(
        fa1Packed: Union[EpsilonNFA, str], fa2Packed: Union[EpsilonNFA, str]
    ):
        if type(fa1Packed) == EpsilonNFA:
            f1 = fa1Packed
        else:
            f1 = nfa_from_string(fa1Packed)
        if type(fa2Packed) == EpsilonNFA:
            f2 = fa2Packed
        else:
            f2 = nfa_from_string(fa2Packed)
        return f1, f2

    def visitExprConcat(self, ctx: LanguageParser.ExprConcatContext):
        fa1Packed, fa2Packed = self.visitChildren(ctx)
        if type(fa1Packed) == str and type(fa2Packed) == str:
            return fa1Packed + fa2Packed

        f1, f2 = Executor.get_2_nfas(fa1Packed, fa2Packed)
        return nfa_concat(f1, f2)

    def visitExprKleene(self, ctx: LanguageParser.ExprKleeneContext):
        fa = self.visitChildren(ctx)
        return nfa_closure(fa)

    def visitExprSetStarts(self, ctx: LanguageParser.ExprSetStartsContext):
        faPacked, startsPacked = self.visitChildren(ctx)
        fa: EpsilonNFA = faPacked.copy()
        startsPacked: set
        for state in faPacked.start_states:
            fa.remove_start_state(state)
        for state in startsPacked:
            fa.add_start_state(state)
        return fa

    def visitExprMap(self, ctx: LanguageParser.ExprMapContext):
        lambda_: LambdaType = self.typeAnnotations.get(ctx.lambda_())
        exprVal: Union[tuple, set] = self.visit(ctx.expr())
        resultSet = set()
        for elem in exprVal:
            self.bindValue(lambda_.pattern, elem)
            self.bindType(lambda_.pattern, lambda_.patternType)
            ret = self.visit(lambda_.body)
            self.unbind(lambda_.pattern)
            resultSet.add(ret)

        return resultSet

    def visitExprProduct(self, ctx: LanguageParser.ExprProductContext):
        fa1Packed, fa2Packed = self.visitChildren(ctx)
        return nfa_production(fa1Packed, fa2Packed)
