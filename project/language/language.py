import sys
from typing import List

from antlr4 import *
from project.language.antlr_out.LanguageParser import LanguageParser
from project.language.antlr_out.LanguageLexer import LanguageLexer
from project.language.antlr_out.LanguageListener import LanguageListener

import pydot


def get_parser(prog: str) -> LanguageParser:
    input_stream = InputStream(prog)
    lexer = LanguageLexer(input_stream)
    stream = CommonTokenStream(lexer)
    return LanguageParser(stream)


def does_belong_to_language(prog: str):
    parser = get_parser(prog)
    parser.removeErrorListeners()
    parser.program()
    return parser.getNumberOfSyntaxErrors() == 0


class DOTBuilder(LanguageListener):
    def __init__(self):
        self._dot = pydot.Dot("Program")
        self._stack: List[pydot.Node] = []
        self._last_id = 0

    def _id(self):
        self._last_id += 1
        return self._last_id

    def _link_to_parent(self, node: pydot.Node):
        if len(self._stack) > 0:
            parent = self._stack[-1]
            edge = pydot.Edge(parent.get_name(), node.get_name())
            self._dot.add_edge(edge)

    def _new_node(self, new_node: str, type: str = "terminal") -> pydot.Node:
        if type == "error":
            new_node = pydot.Node(self._id(), label=new_node, color="red")
        elif type == "terminal":
            new_node = pydot.Node(self._id(), label=new_node)
        elif type == "rule":
            new_node = pydot.Node(self._id(), label=new_node, color="darkgray")

        self._dot.add_node(new_node)
        self._link_to_parent(new_node)
        return new_node

    def visitTerminal(self, node: TerminalNode):
        super().visitTerminal(node)
        self._new_node(str(node))

    def visitErrorNode(self, node: ErrorNode):
        super().visitErrorNode(node)
        self._new_node(f'ERROR: "{node!s}"', "error")

    def enterEveryRule(self, ctx: ParserRuleContext):
        super().enterEveryRule(ctx)
        ruleName = LanguageParser.ruleNames[ctx.getRuleIndex()]
        node = self._new_node(f"rule: {ruleName}", "rule")
        self._stack.append(node)

    def exitEveryRule(self, ctx: ParserRuleContext):
        super().exitEveryRule(ctx)
        self._stack.pop()

    @staticmethod
    def build(prog: str) -> pydot.Dot:
        parser = get_parser(prog)
        dotBuilder = DOTBuilder()
        walker = ParseTreeWalker()
        walker.walk(dotBuilder, parser.program())
        return dotBuilder._dot
