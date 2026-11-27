from ....symbol_types import *
from .base import BaseBuilder
from AST.base import *
from ...helpers import v_args


class ExpressionBuilder(BaseBuilder):
    __only_namespace__ = True
    targets = (ExprAST,)

    def visit_NumberAST(self, node):
        return self.create(
            NumberSymbol,
            node,
            value=node.value,
        )

    def visit_IdentifierAST(self, node):
        return self.create(
            IdentifierSymbol,
            node,
            name=node.name,
        )

    def visit_StringAST(self, node):
        return self.create(
            StringSymbol,
            node,
            value=node.value,
        )

    @v_args(childs=True)
    def visit_BinaryOpAST(self, node, childs):
        self.create(BinaryOpSymbol, node, **childs)
