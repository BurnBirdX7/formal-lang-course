from typing import List, Union

from antlr4 import ParserRuleContext


class ParseTypeError(StopIteration):
    def __init__(self, msg: str):
        super().__init__(msg)


class Type:
    def __eq__(self, other):
        return type(self) == type(other)

    def __str__(self):
        return type(self).__name__


class NoneType(Type):
    pass


class VarType(Type):
    def __init__(self, name: str):
        self.name = name

    def __str__(self):
        return self.name


class BoolType(Type):
    pass


class IntType(Type):
    pass


class SetType(Type):
    def __init__(self, element_type: Type):
        self.element_type = element_type

    def __str__(self):
        return "SetType<" + str(self.element_type) + ">"

    def __eq__(self, other):
        return super().__eq__(other) and self.element_type == other.element_type


class StringType(Type):
    pass


class FAType(Type):
    def __init__(self, vertex_type: Type = IntType):
        self.vertexType = vertex_type

    def __str__(self):
        return f"FAType<{self.vertexType!s}>"


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


class PatternType(Type):
    def __init__(self, typeDescription: List[Union[VarType, "PatternType"]]):
        self.description = typeDescription

    def __str__(self):
        patternNames = map(str, self.description)
        return "p[" + ", ".join(patternNames) + "]"

    def __len__(self):
        return len(self.description)


class LambdaType(Type):
    def __init__(
        self,
        pattern: PatternType,
        patternType: TupleType,
        return_type: Type,
        subtree: ParserRuleContext,
    ):
        self.pattern = pattern
        self.patternType = patternType
        self.returnType = return_type
        self.subtree = subtree

    def __str__(self):
        return f"LambdaType<{self.patternType} -> {self.returnType}>"
