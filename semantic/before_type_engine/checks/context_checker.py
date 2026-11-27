from utils.errors import *
from AST.base import *
from ..helpers import v_args
from ...symbol_types import *


class ContextChecker:
    targets = (PassAST, ReturnAST, ContinueAST, BreakAST)

    def has_ancestor(self, parent, types):
        while parent is not None:
            if isinstance(parent.this, types):
                return True

            parent = parent.parent

        return False

    def require_ancestor(self, node, parent, types, message):
        if not self.has_ancestor(parent, types):
            raise NidavellirSemanticError(message, node.line)

    @v_args(parent=True)
    def visit_PassAST(self, node, parent):
        self.require_ancestor(
            node,
            parent,
            (FunctionAST, ClassAST),
            "pass statement outside of function or class",
        )

    @v_args(parent=True)
    def visit_BreakAST(self, node, parent):
        self.require_ancestor(
            node,
            parent,
            (ForAST, WhileAST),
            "break statement outside of loop",
        )

    @v_args(parent=True)
    def visit_ContinueAST(self, node, parent):
        self.require_ancestor(
            node,
            parent,
            (ForAST, WhileAST),
            "continue statement outside of loop",
        )

    @v_args(parent=True)
    def visit_ReturnAST(self, node, parent):
        self.require_ancestor(
            node,
            parent,
            FunctionAST,
            "return statement outside of function",
        )
