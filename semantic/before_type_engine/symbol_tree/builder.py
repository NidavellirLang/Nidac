from .symbol_table import Scope, SymbolTableManager
from ...symbol_types import *
from ..helpers import vc_args, v_args
from .builders.base import BaseBuilder
from type_systems.types import resolve_type, ClassType
from utils.errors import *
from AST.base import *


@vc_args(ctx=True)
class SymbolTreeBuilder(BaseBuilder):
    __slots__ = ("symbol_table", "symbol_tree", "ctx")

    def __init__(self, ctx):
        self.ctx = ctx
        self.symbol_table = SymbolTableManager()
        ctx["symbol_table"] = self.symbol_table
        self.symbol_tree = []

    def resolve_type(self, type):
        resolved = resolve_type(type)

        if resolved is None and isinstance(type, str):
            if isinstance(self.stm.lookup_class_name(type), ClassSymbol):
                return ClassType(type)

        return resolved

    @v_args(parent=True)
    def visit(self, node, parent=None):
        symbol = self.symbol_table.lookup_symbol_id(self.get_id(node))
        if symbol is None:
            raise NidavellirInternalError(
                f"Symbol not created for: {node.__class__.__name__}", line=node.line
            )
        if parent is None:
            self.symbol_tree.append(symbol)

        if hasattr(symbol, "type") and isinstance(symbol.type, str):
            symbol.type = self.resolve_type(symbol.type)

    def on_end(self):
        print("\n".join(map(str, self.symbol_tree)))
