from ....symbol_types import *
from AST.base import *
from .base import BaseBuilder
from ...helpers import *


class StatementBuilder(BaseBuilder):
    __only_namespace__ = True
    targets = (StmtAST,)

    def on_enter_scope(self, ast):
        self.symbol_table.enter_scope()

    def on_exit_scope(self, ast):
        self.symbol_table.exit_scope()

    def get_parent_assign(self, ast):
        if not isinstance(ast.target, IdentifierAST):
            return None

        return self.symbol_table.lookup_assignment_name(ast.target.name)

    @v_args(childs=True)
    def visit_FunctionAST(self, ast, childs=None):
        name = ast.name.name
        symbol = self.create(FunctionSymbol, ast, **childs)
        self.symbol_table.define_func_name(name, symbol)
        return symbol

    def visit_PassAST(self, ast):
        return self.create(PassSymbol, ast)

    @v_args(childs=True)
    def visit_DeclareAST(self, node, childs=None):
        name = node.target.name
        symbol = self.create(AssignSymbol, node, value=None, **childs)
        self.symbol_table.define_assignment_name(name, symbol)
        return symbol

    @v_args(childs=True)
    def visit_AssignAST(self, node, childs=None):
        parent_assign = self.get_parent_assign(node)

        declared_type = parent_assign.type if parent_assign is not None else node.type

        symbol = self.create(
            AssignSymbol,
            node,
            type=declared_type,
            parent_assign=parent_assign,
            **childs
        )

        if parent_assign is None:
            self.symbol_table.define_assignment_name(
                node.target.name,
                symbol,
            )
        else:
            parent_assign.uses.append(symbol)

        return symbol
