from ....symbol_types import *
from .base import BaseBuilder
from AST.base import *
from ...helpers import v_args
from utils.errors import *


class ExpressionBuilder(BaseBuilder):
    __only_namespace__ = True
    targets = (ExprAST,)

    # HELPERS

    def get_variable_target(self, variable):
        variable_name = variable.name
        lk = self.symbol_table.lookup_assignment_name(variable_name)
        if lk is None:
            lk = self.symbol_table.lookup_func_name(variable_name)

        if lk is None:
            lk = self.symbol_table.lookup_class_name(variable_name)

        if lk is None:
            raise NidavellirNameError(
                f"Name '{variable_name}' not found", variable.line
            )

        return lk

    # visitors

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

    def visit_VariableAST(self, node):
        lk = self.get_variable_target(node)
        return self.create(
            VariableSymbol,
            node,
            name=lk.target if hasattr(lk, "target") else lk.name,
            lookup=lk,
        )

    @v_args(childs=True)
    def visit_BinaryOpAST(self, node, childs):
        op = node.op
        return self.create(BinaryOpSymbol, node, op=op, **childs)

    @v_args(childs=True)
    def visit_CallAST(self, node, childs):
        if isinstance(node.target, VariableAST):
            name = node.target.name
            lk = self.symbol_table.lookup_func_name(name)

            symbol = self.create(
                CallSymbol,
                node,
                lookup=lk,
                **childs,
            )

            lk.uses.append(symbol)
            return symbol

        elif isinstance(node.target, FieldAccessAST):
            return self.create(
                CallSymbol,
                node,
                **childs,
            )
        else:
            raise Exception(node)
