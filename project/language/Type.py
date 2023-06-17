from typing import List


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
    pass


class IntType(Type):
    pass


class TypedSetType(Type):
    def __init__(self, element_type: Type):
        self.elementType = element_type

    def __str__(self):
        return "SetType<" + str(self.elementType) + ">"

    def __eq__(self, other):
        return super().__eq__(other) and self.elementType == other.elementType


class StringType(Type):
    pass


class FAType(Type):
    pass


class RSMType(Type):
    pass


class TupleType(Type):
    def __init__(self, description: List[Type]):
        self.description = description

    def __str__(self):
        typeNames = map(str, self.description)
        return "(" + ", ".join(typeNames) + ")"

    def __eq__(self, other):
        return super().__eq__(other) and self.description == other.description

    def __len__(self):
        return len(self.description)


class PatternType(TupleType):
    def __init__(self, typeDescription: List[Type], nameDescription: List[str]):
        super().__init__(typeDescription)
        assert len(typeDescription) == len(nameDescription)
        self.names = nameDescription

    def __str__(self):
        typeNames = map(str, self.description)
        nvs = []
        for typeN, varN in zip(typeNames, self.names):
            if varN == "//pattern//":
                nvs.append(str(typeN))
            else:
                nvs.append(str(varN))

        return "[" + ", ".join(nvs) + "]"

    def __len__(self):
        return len(self.description)
