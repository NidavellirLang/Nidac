from .symbol_types import *
from nida_ast.base import *
from utils.errors import *
from utils.hashability import ishashable


class SymbolRegistry:
    __slots__ = (
        "norm_assignments",
        "norm_functions",
        "norm_classes",
        "symbols_by_id",
    )

    def __init__(self):
        self.norm_assignments = {}
        self.norm_functions = {}
        self.norm_classes = {}
        self.symbols_by_id = {}

    def _define(self, table, name, symbol, category):
        if name in table and not isinstance(table[name], UnavailableSymbol):
            raise NidavellirSemanticError(
                f"{category} '{name}' already exists in scope "
                "and cannot be redefined",
                symbol.ast_node.line,
            )

        table[name] = symbol
        return symbol

    # Analyzer API: normal names.

    def define_assignment(self, name, symbol):
        self._define(self.norm_assignments, name, symbol, "Assignment")

    def define_func(self, name, symbol):
        return self._define(self.norm_functions, name, symbol, "Function")

    def define_class(self, name, symbol):
        return self._define(self.norm_classes, name, symbol, "Class")

    # Global symbol registry: all symbol categories share one ID namespace.

    def define_symbol_id(self, symbol_id, symbol):
        existing = self.symbols_by_id.get(symbol_id)

        if existing is not None:
            if symbol is None:
                raise Exception()
            if existing.ast_node is symbol.ast_node:
                self.symbols_by_id[symbol_id] = symbol
                return symbol

            raise NidavellirInternalError(
                f"Duplicate symbol ID '{symbol_id}'",
                symbol.ast_node.line,
            )

        self.symbols_by_id[symbol_id] = symbol
        return symbol

    def lookup_symbol_id(self, symbol_id):
        return self.symbols_by_id.get(symbol_id)


class Scope:
    __slots__ = ("parent", "registry", "scope_type")

    def __init__(self, parent=None, scope_type=None):
        self.parent = parent
        self.registry = SymbolRegistry()
        self.scope_type = scope_type

    # Analyzer lookups: normal names.

    def _lookup_name(self, name, category):
        scope = self
        while scope is not None:
            if not ishashable(name):
                return None

            symbol = getattr(scope.registry, category).get(name)
            if symbol is not None:
                return symbol

            scope = scope.parent

        return None

    def lookup_assignment_name(self, name):
        return self._lookup_name(name, "norm_assignments")

    def lookup_func_name(self, name):
        return self._lookup_name(name, "norm_functions")

    def lookup_class_name(self, name):
        return self._lookup_name(name, "norm_classes")

    # Definitions: current scope only.

    def define_assignment(self, name, symbol):
        return self.registry.define_assignment(name, symbol)

    def define_func(self, name, symbol):
        return self.registry.define_func(name, symbol)

    def define_class(self, name, symbol):
        return self.registry.define_class(name, symbol)

    # Global symbol ID registration.

    def define_symbol_id(self, symbol_id, symbol):
        return self.registry.define_symbol_id(symbol_id, symbol)

    def lookup_symbol_id(self, symbol_id):
        return self.registry.lookup_symbol_id(symbol_id)


class SymbolTableManager:
    __slots__ = ("global_scope", "current_scope")

    def __init__(self):
        self.global_scope = Scope()
        self.current_scope = self.global_scope

    def enter_scope(self, scope_type=None):
        scope = Scope(
            parent=self.current_scope,
            scope_type=scope_type,
        )
        self.current_scope = scope
        return scope

    def exit_scope(self):
        parent = self.current_scope.parent

        if parent is None:
            raise NidavellirInternalError("Cannot exit global scope")

        self.current_scope = parent

    # Analyzer API: normal-name lookups.

    def lookup_assignment_name(self, name):
        return self.current_scope.lookup_assignment_name(name)

    def lookup_func_name(self, name):
        return self.current_scope.lookup_func_name(name)

    def lookup_class_name(self, name):
        return self.current_scope.lookup_class_name(name)

    # Definitions register the name in the current scope and the ID globally.

    def define_assignment_norm(self, name, symbol):
        self.current_scope.define_assignment(name, symbol)
        return symbol

    def define_assignment_id(self, symbol_id, symbol):
        self.global_scope.define_symbol_id(symbol_id, symbol)
        return symbol

    def define_assignment(self, name, symbol_id, symbol):
        self.current_scope.define_assignment(name, symbol)
        self.global_scope.define_symbol_id(symbol_id, symbol)
        return symbol

    def define_func(self, name, symbol_id, symbol):
        self.current_scope.define_func(name, symbol)
        self.global_scope.define_symbol_id(symbol_id, symbol)
        return symbol

    def define_class(self, name, symbol_id, symbol):
        self.current_scope.define_class(name, symbol)
        self.global_scope.define_symbol_id(symbol_id, symbol)
        return symbol

    # Public ID lookups: one global namespace.

    def lookup_symbol_id(self, symbol_id):
        return self.global_scope.lookup_symbol_id(symbol_id)

    def define_symbol_id(self, symbol_id, symbol):
        return self.global_scope.define_symbol_id(symbol_id, symbol)

    # Compatibility helpers; remove these once all callers use lookup_symbol_id.

    def lookup_assignment_id(self, symbol_id):
        symbol = self.lookup_symbol_id(symbol_id)
        return symbol if isinstance(symbol, AssignSymbol) else None

    def lookup_func_id(self, symbol_id):
        symbol = self.lookup_symbol_id(symbol_id)
        return symbol if isinstance(symbol, FunctionSymbol) else None

    def lookup_class_id(self, symbol_id):
        symbol = self.lookup_symbol_id(symbol_id)
        return symbol if isinstance(symbol, ClassSymbol) else None
