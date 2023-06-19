from typing import List, Union, Any

from antlr4 import ParserRuleContext

from project.language.Value import *


class ParseTypeError(RuntimeError):
    def __init__(self, msg: str):
        super().__init__(msg)
        self.value = msg


class Type:
    def __eq__(self, other):
        return type(self) == type(other)

    def __str__(self):
        return type(self).__name__

    def is_type(self, val: Any):
        raise NotImplementedError()


class NoneType(Type):
    def is_type(self, val: Any):
        return val is None


class VarType(Type):
    def __init__(self, name: str):
        self.name = name

    def __str__(self):
        return self.name


class BoolType(Type):
    def is_type(self, val: Any):
        return type(val) == bool


class IntType(Type):
    def is_type(self, val: Any):
        return type(val) == int


class SetType(Type):
    def __init__(self, element_type: Type):
        self.element_type = element_type

    def __str__(self):
        return "SetType<" + str(self.element_type) + ">"

    def __eq__(self, other):
        return super().__eq__(other) and self.element_type == other.element_type

    def is_type(self, val: Any):
        if type(val) != SetValue:
            return False
        val: SetValue
        for elem in val.value:
            if not self.element_type.is_type(elem):
                return False
        return True


class StringType(Type):
    def is_type(self, val: Any):
        return type(val) == str


class FAType(Type):
    def __init__(self, vertex_type: Type = IntType):
        self.vertexType = vertex_type

    def __str__(self):
        return f"FAType<{self.vertexType!s}>"

    def __eq__(self, other):
        return super().__eq__(other) and self.vertexType == other.vertexType

    def is_type(self, val: Any):
        return type(val) == FAValue


class TupleType(Type):
    def __init__(self, description: List[Type]):
        self.description = description

    def __str__(self):
        typeNames = map(str, self.description)
        return "t[" + ", ".join(typeNames) + "]"

    def __eq__(self, other):
        return super().__eq__(other) and self.description == other.description

    def __len__(self):
        return len(self.description)

    def is_uniform(self) -> bool:
        firstType = self.description[0]
        for typ in self.description[1:]:
            if firstType != typ:
                return False

        return True

    @property
    def element_type(self) -> Type:
        if self.is_uniform():
            return self.description[0]
        raise ParseTypeError("Tried to get element type for not uniform tuple")

    def is_type(self, val: Any):
        if type(val) != TupleValue:
            return False
        for (elem, typ) in zip(val.value, self.description):
            if not typ.is_type(elem):
                return False
        return True


class PatternType(Type):
    def __init__(self, typeDescription: List[Union[VarType, "PatternType"]]):
        self.description = typeDescription

    def __str__(self):
        patternNames = map(str, self.description)
        return "p[" + ", ".join(patternNames) + "]"

    def __len__(self):
        return len(self.description)

    def __eq__(self, other):
        return super().__eq__(other) and self.description == other.description


class LambdaType(Type):
    def __init__(
        self,
        pattern: PatternType,
        pattern_type: TupleType,
        return_type: Type,
        body: ParserRuleContext,
        associated_expr: ParserRuleContext,
    ):
        self.pattern = pattern
        self.patternType = pattern_type
        self.returnType = return_type
        self.body = body
        self.associatedExpression = associated_expr

    def __str__(self):
        return f"LambdaType<{self.patternType} -> {self.returnType}>"

    def is_type(self, val: Any):
        return val is None  # Lambda has no value
