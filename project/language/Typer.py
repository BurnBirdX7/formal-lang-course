import sys
from typing import Dict, Optional

from antlr4 import *
from project.language.antlr_out.LanguageListener import LanguageListener
from project.language.antlr_out.LanguageParser import LanguageParser
from project.language.Type import *


class Typer(LanguageListener):
    def __init__(self):
        self.typeAnnotations: Dict[ParserRuleContext, Type] = {}
        self.variableTypes: Dict[str, Type] = {}
        self.instantPatternBinding: Dict[LanguageParser.PatternContext, Type] = {}
        self.boundContexts: Dict[
            LanguageParser.LambdaContext, LanguageParser.ExprContext
        ] = {}

    def exitPrint(self, ctx: LanguageParser.PrintContext):
        self.typeAnnotations[ctx] = NoneType()

    def exitBind(self, ctx: LanguageParser.BindContext):
        self.typeAnnotations[ctx] = NoneType()

        patternCtx = ctx.pattern()
        patternType = self.typeAnnotations.get(patternCtx)

        exprCtx = ctx.expr()
        exprType = self.typeAnnotations.get(exprCtx)

        self.bindToValue(patternType, exprType)  # type: ignore

    def bindToValue(self, patternType: Union[VarType, PatternType], exprType: Type):
        if type(patternType) == VarType:
            if patternType.name in self.variableTypes:
                raise ParseTypeError(f"Binding of {patternType.name} already exists")
            self.variableTypes[patternType.name] = exprType
            return

        if type(patternType) != PatternType:
            raise ParseTypeError(f"Unexpected pattern type: {patternType}")

        if type(exprType) == TupleType:
            self.bindToTuple(patternType, exprType)  # type: ignore
        else:
            raise ParseTypeError(f"Binding {patternType} to {exprType} is impossible")

    def bindToTuple(self, pattern: PatternType, tupleType: TupleType):
        error_template = f"Binding {pattern} to {tupleType}: "

        if len(pattern) != len(tupleType):
            raise ParseTypeError(
                f"{error_template}pattern and tuple must be the same length"
            )

        for subpattern, typ in zip(pattern.description, tupleType.description):
            self.bindToValue(subpattern, typ)

    def unbind(self, pattern: Union[VarType, PatternType]):
        if type(pattern) == VarType:
            self.unbindVar(pattern.name)
        else:
            self.unbindPattern(pattern)

    def unbindVar(self, name: str):
        if name not in self.variableTypes:
            raise ParseTypeError(f"Trying to unbind not bound variable {name}")
        self.variableTypes.pop(name)

    def unbindPattern(self, pattern: PatternType):
        for subpattern in pattern.description:
            self.unbind(subpattern)

    # Patterns
    def exitPatternVar(self, ctx: LanguageParser.PatternVarContext):
        typ = VarType(ctx.VAR().getText())
        self.typeAnnotations[ctx] = typ
        if ctx in self.instantPatternBinding:
            self.bindToValue(typ, self.instantPatternBinding[ctx])

    def exitPatternPattern(self, ctx: LanguageParser.PatternPatternContext):
        def get_type(ctx: LanguageParser.PatternContext) -> PatternType:
            return self.typeAnnotations.get(ctx)  # type: ignore

        patternTypeList = list(map(get_type, ctx.pattern()))
        typ = PatternType(patternTypeList)
        self.typeAnnotations[ctx] = typ
        if ctx in self.instantPatternBinding:
            self.bindToValue(typ, self.instantPatternBinding[ctx])

    # Tuples
    def exitTuple(self, ctx: LanguageParser.TupleContext):
        def get_type(ctx: LanguageParser.TupleContext):
            return self.typeAnnotations.get(ctx)

        tupleTypeList = list(map(get_type, ctx.val()))
        self.typeAnnotations[ctx] = TupleType(tupleTypeList)

    # Values
    def exitVal(self, ctx: LanguageParser.ValContext):
        # type
        if ctx.STRING():
            self.typeAnnotations[ctx] = StringType()
        elif ctx.INT():
            self.typeAnnotations[ctx] = IntType()
        elif ctx.intSet():
            self.typeAnnotations[ctx] = SetType(IntType())
            self.typeAnnotations[ctx.intSet()] = SetType(IntType())
        elif ctx.tuple_():
            self.typeAnnotations[ctx] = self.typeAnnotations.get(ctx.tuple_())

    # Lambda
    def enterLambda(self, ctx: LanguageParser.LambdaContext):
        parentCtx = ctx.parentCtx
        parentCtxType = type(parentCtx)

        if (
            parentCtxType != LanguageParser.ExprMapContext
            and parentCtxType != LanguageParser.ExprFilterContext
        ):
            raise ParseTypeError(
                f"Lambda only can be part of Map or Filter expression, got {parentCtxType}"
            )

        parentCtx: Union[
            LanguageParser.ExprMapContext, LanguageParser.ExprFilterContext
        ] = ctx.parentCtx
        expr = parentCtx.expr()
        exprType = self.typeAnnotations.get(expr)  # type: ignore
        if type(exprType) != TupleType and type(exprType) != SetType:
            raise ParseTypeError(
                f"{parentCtx.getText()}: Lambda cannot be bound to the type {exprType}"
            )

        if type(exprType) == TupleType and not exprType.is_uniform():
            raise ParseTypeError(
                f"Tuple must be uniform to be bound to lambda, got {exprType}"
            )

        self.instantPatternBinding[ctx.pattern()] = exprType.element_type
        self.boundContexts[ctx] = expr

    def exitLambda(self, ctx: LanguageParser.LambdaContext):
        pattern = self.typeAnnotations[ctx.pattern()]
        patternType = self.instantPatternBinding.get(ctx.pattern())
        returnType = self.typeAnnotations[ctx.expr()]
        self.typeAnnotations[ctx] = LambdaType(
            pattern,  # type: ignore
            patternType,  # type: ignore
            returnType,
            ctx.expr(),
            self.boundContexts.get(ctx),
        )
        self.unbind(pattern)  # type: ignore

    # Expression parsing
    def exitExprVar(self, ctx: LanguageParser.ExprVarContext):
        varName = ctx.VAR().getText()
        if varName not in self.variableTypes:
            raise ParseTypeError(f"{varName} variable wasn't defined")

        self.typeAnnotations[ctx] = self.variableTypes.get(varName)

    def exitExprVal(self, ctx: LanguageParser.ExprValContext):
        self.typeAnnotations[ctx] = self.typeAnnotations.get(ctx.val())

    # FA Manipulation
    def exitExprSetStarts(self, ctx: LanguageParser.ExprSetFinalsContext):
        fa, vertices = ctx.expr()
        faType: FAType = self.typeAnnotations.get(fa)
        if type(faType) != FAType:
            raise ParseTypeError(
                f"{ctx.getText()}: FAType<...> was expected not {faType}"
            )

        verticesType = self.typeAnnotations.get(vertices)
        expectedType = SetType(faType.vertexType)
        if expectedType != verticesType:
            raise ParseTypeError(
                f"{ctx.getText()}: {expectedType} was expected not {verticesType}"
            )

        self.typeAnnotations[ctx] = faType

    exitExprSetFinals = exitExprSetStarts  # Same type

    def exitExprAddStarts(self, ctx: LanguageParser.ExprAddStartsContext):
        vertices, fa = ctx.expr()
        faType: FAType = self.typeAnnotations.get(fa)
        if type(faType) != FAType:
            raise ParseTypeError(
                f"{ctx.getText()}: FAType<...> was expected not {faType}"
            )

        verticesType = self.typeAnnotations.get(vertices)
        expectedType = SetType(faType.vertexType)
        if expectedType != verticesType:
            raise ParseTypeError(
                f"{ctx.getText()}: {expectedType} was expected not {verticesType}"
            )

        self.typeAnnotations[ctx] = faType

    exitExprAddFinals = exitExprAddStarts

    def exitExprGetFinals(self, ctx: LanguageParser.ExprGetFinalsContext):
        typ = self.typeAnnotations.get(ctx.expr())
        if type(typ) != FAType:
            raise ParseTypeError(f"{ctx.getText()}: Cant get vertices from {typ}")
        self.typeAnnotations[ctx] = SetType(typ.vertexType)

    exitExprGetStarts = exitExprGetFinals
    exitExprGetVertices = exitExprGetFinals

    def exitExprGetReachable(self, ctx: LanguageParser.ExprGetReachableContext):
        typ = self.typeAnnotations.get(ctx.expr())
        if type(typ) != FAType:
            raise ParseTypeError(
                f"{ctx.getText()}: Cant get reachable pairs from {typ}"
            )

        self.typeAnnotations[ctx] = SetType(TupleType([typ.vertexType, typ.vertexType]))

    def exitExprGetEdges(self, ctx: LanguageParser.ExprGetEdgesContext):
        fa = self.typeAnnotations[ctx.expr()]
        if type(fa) != FAType:
            raise ParseTypeError(f"{ctx.getText()}: Cannot get edges from {fa}")

        vertexType = fa.vertexType
        edgeType = TupleType([vertexType, StringType(), vertexType])
        self.typeAnnotations[ctx] = SetType(edgeType)

    def exitExprGetLabels(self, ctx: LanguageParser.ExprGetLabelsContext):
        fa = self.typeAnnotations[ctx.expr()]
        if type(fa) != FAType:
            raise ParseTypeError(f"{ctx.getText()}: Cannot get labels from {fa}")
        self.typeAnnotations[ctx] = SetType(StringType())

    def exitExprLoad(self, ctx: LanguageParser.ExprLoadContext):
        if ctx.VAR():
            if self.variableTypes[ctx.VAR().getText()] != StringType():
                raise ParseTypeError(
                    "Load expression must contain String literal or String-typed variable"
                )
        if ctx.val():
            if self.typeAnnotations.get(ctx.val()) != StringType():
                raise ParseTypeError(
                    "Load expression must contain String literal or String-typed variable"
                )

        self.typeAnnotations[ctx] = FAType(IntType())

    # Map
    def exitExprMap(self, ctx: LanguageParser.ExprMapContext):
        lambda_ = ctx.lambda_()
        lambdaType: LambdaType = self.typeAnnotations.get(lambda_)  # type: ignore

        if type(lambdaType) != LambdaType:
            raise ParseTypeError(f'{ctx.getText()}: Lambda should be after "with"')

        self.typeAnnotations[ctx] = SetType(lambdaType.returnType)

    def exitExprFilter(self, ctx: LanguageParser.ExprFilterContext):
        lambda_ = ctx.lambda_()
        lambdaType: LambdaType = self.typeAnnotations.get(lambda_)  # type: ignore

        if type(lambdaType) != LambdaType:
            raise ParseTypeError(f'{ctx.getText()}: Lambda should be after "with"')

        if lambdaType.returnType != BoolType():
            raise ParseTypeError(
                f"{ctx.getText()}: Lambda must be a predicate (return bool)"
            )

        expr = ctx.expr()
        exprType = self.typeAnnotations.get(expr)

        if (type(exprType) != SetType and type(exprType) != TupleType) or (
            type(exprType) == TupleType and not exprType.is_uniform()
        ):
            raise ParseTypeError(
                f"{ctx.getText()}: Filter can be applied only to sets and uniform tuples,"
                f" got {exprType}"
            )

        self.typeAnnotations[ctx] = SetType(exprType.element_type)

    # FA Manipulation

    def productCompat(self, t1, t2) -> Optional[Type]:
        setProd = self.setProductCompat(t1, t2)
        if setProd is not None:
            return setProd

        return self.setProductCompat(t1, t2) or self.languageProductCompat(t1, t2)

    def setProductCompat(self, t1, t2) -> Optional[Type]:
        if type(t1) == SetType and t1 == t2:
            return t1

    def languageProductCompat(self, t1, t2) -> Optional[Type]:
        faType = FAType(IntType())
        p1 = t1 == faType or t1 == StringType()
        p2 = t2 == faType or t2 == StringType()
        if p1 and p2 and t1 != t2:
            return FAType(TupleType([IntType(), IntType()]))
        if type(t1) == FAType and type(t2) == FAType:
            return FAType(TupleType([t1.vertexType, t2.vertexType]))

    def exitExprProduct(self, ctx: LanguageParser.ExprProductContext):
        t1, t2 = ctx.expr()
        t1 = self.typeAnnotations.get(t1)
        t2 = self.typeAnnotations.get(t2)
        typ = self.productCompat(t1, t2)
        if not typ:
            raise ParseTypeError(
                f'"{ctx.getText()}: operation is impossible between' f" {t1} and {t2}"
            )
        self.typeAnnotations[ctx] = typ

    def concatCompat(self, t1, t2) -> Optional[Type]:
        if t1 == StringType() and t2 == StringType():
            return StringType()

        if t1 == StringType() and t2 == FAType(IntType()):
            return t2

        if t1 == FAType(IntType()) and t2 == StringType():
            return t1

        if t1 == FAType(IntType()) and t2 == FAType(IntType()):
            return t1

    def exitExprConcat(self, ctx: LanguageParser.ExprConcatContext):
        t1, t2 = ctx.expr()
        t1 = self.typeAnnotations.get(t1)
        t2 = self.typeAnnotations.get(t2)
        typ = self.concatCompat(t1, t2)
        if not typ:
            raise ParseTypeError(
                f'"{ctx.getText()}: operation is not possible between"'
                f" {t1} and {t2}"
            )
        self.typeAnnotations[ctx] = typ

    @staticmethod
    def unionCompat(t1, t2) -> Optional[Type]:
        type_group = [StringType(), FAType(IntType())]
        if t1 in type_group and t2 in type_group:
            return FAType(IntType())

        if type(t1) == SetType and t1 == t2:
            return t2

    def exitExprUnion(self, ctx: LanguageParser.ExprUnionContext):
        t1, t2 = ctx.expr()
        t1 = self.typeAnnotations.get(t1)
        t2 = self.typeAnnotations.get(t2)
        typ = self.unionCompat(t1, t2)
        if not typ:
            raise ParseTypeError(
                f"{ctx.getText()}: operation is not possible between" f" {t1} and {t2}"
            )

        self.typeAnnotations[ctx] = typ

    def exitExprTransition(self, ctx: LanguageParser.ExprTransitionContext):
        t1 = ctx.expr()
        t1 = self.typeAnnotations.get(t1)
        if type(t1) != FAType:
            raise ParseTypeError(
                f'"{ctx.getText()}: operation is possible only with FA"'
            )
        self.typeAnnotations[ctx] = t1

    exitExprKleene = exitExprTransition

    # bool
    def exitExprIn(self, ctx: LanguageParser.ExprInContext):
        val, setVal = ctx.expr()
        valType = self.typeAnnotations.get(val)
        setType = self.typeAnnotations.get(setVal)  # type: ignore

        if type(setType) != SetType and type(setType) != TupleType:
            raise ParseTypeError(
                f"{ctx.getText()}: operation is possible with sets and tuples"
            )

        if setType.element_type != valType:
            raise ParseTypeError(
                f"{ctx.getText()}: its impossible to check value of type {valType} in {setType}"
            )

        self.typeAnnotations[ctx] = BoolType()

    def exitExprBraced(self, ctx: LanguageParser.ExprBracedContext):
        self.typeAnnotations[ctx] = self.typeAnnotations.get(ctx.expr())

    def visitErrorNode(self, node: ErrorNode):
        super().visitErrorNode(node)
        raise ParseTypeError(
            f"Error Node is detected, Typing and Execution is unavailable, {node}"
        )
