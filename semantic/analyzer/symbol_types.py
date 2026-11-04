from type_systems.types import resolve_type, StringType, NoneType, ClassType, Type
from dataclasses import dataclass, fields, field as dc_field
from nida_ast.base import AST, IntrinsicAST


@dataclass(slots=True, repr=False, kw_only=True)
class Symbol:

    # Class attributes with type hints
    type: Type | None = None  # Type of the symbol, can be None
    ast_node: AST | None = None  # Associated AST node, can be None
    uses: list[Symbol] = dc_field(default_factory=list)  # List of symbol uses

    # Formatting configuration constants
    _FORMAT_SKIP = {"ast_node"}  # Attributes to skip during formatting
    _FORMAT_MAX_ITEMS = 5  # Maximum number of items to show in collections
    _FORMAT_MAX_DEPTH = 2
    _FORMAT_MAX_VALUE_LEN = 100  # Maximum length of string representation

    @staticmethod
    def _symbol_ref(value):

        # Create a string representation of a symbol reference
        cls = type(value).__name__
        # Get the class name of the value
        # Try to get name or value attribute
        name = getattr(value, "name", None)
        if name is None:
            name = getattr(value, "value", None)

        # Get the type of the symbol if available
        symbol_type = getattr(value, "type", None)
        # Build parts of the reference string

        parts = [cls]

        if name is not None:
            parts.append(repr(name))

        if symbol_type is not None:
            type_name = type(symbol_type).__name__
            parts.append(f"type={type_name}")

        # Add memory address for unique identification
        parts.append(f"@{id(value):x}")

        return f"<{' '.join(parts)}>"

    @classmethod
    def _format_value(cls, value):
        if isinstance(value, Symbol):
            return cls._symbol_ref(value)

        if isinstance(value, list):
            count = len(value)
            if not count:
                return "[]"

            items = [cls._format_value(v) for v in value[: cls._FORMAT_MAX_ITEMS]]

            suffix = f", ... +{count - len(items)}" if count > len(items) else ""
            return f"[{', '.join(items)}{suffix}]"

        if isinstance(value, dict):
            count = len(value)
            if not count:
                return "{}"

            items = [
                f"{k!r}: {cls._format_value(v)}"
                for k, v in list(value.items())[: cls._FORMAT_MAX_ITEMS]
            ]

            suffix = f", ... +{count - len(items)}" if count > len(items) else ""
            return f"{{{', '.join(items)}{suffix}}}"

        if hasattr(value, "__dict__"):
            cls_name = type(value).__name__

            name = getattr(value, "name", None)
            node_id = getattr(value, "node_id", None)

            parts = [cls_name]

            if name is not None:
                parts.append(repr(name))

            if node_id is not None:
                parts.append(f"id={node_id}")

            return f"<{' '.join(parts)} @{id(value):x}>"

        if type(value).__name__.endswith("Type"):
            return repr(value)

        result = repr(value)

        limit = cls._FORMAT_MAX_VALUE_LEN
        if len(result) > limit:
            result = result[: limit - 3] + "..."

        return result

    def _format(
        self,
        indent=0,
        seen=None,
        *,
        verbose=False,
        max_depth=None,
        max_items=None,
    ):
        if seen is None:
            seen = set()

        if max_depth is None:
            max_depth = self._FORMAT_MAX_DEPTH

        if max_items is None:
            max_items = self._FORMAT_MAX_ITEMS

        prefix = "  " * indent
        class_name = type(self).__name__

        if id(self) in seen:
            return f"{prefix}{self._symbol_ref(self)}"

        seen.add(id(self))

        attrs = {
            k: v
            for k, v in vars(self).items()
            if not k.startswith("_") and k not in self._FORMAT_SKIP
        }

        if not attrs:
            seen.remove(id(self))
            return f"{prefix}{class_name}()"

        lines = [f"{prefix}{class_name}:"]

        for key, value in attrs.items():
            field_prefix = f"{prefix}  {key}:"

            if isinstance(value, Symbol):
                if verbose and indent < max_depth:
                    lines.append(field_prefix)
                    lines.append(
                        value._format(
                            indent + 2,
                            seen,
                            verbose=True,
                            max_depth=max_depth,
                            max_items=max_items,
                        )
                    )
                else:
                    lines.append(f"{field_prefix} {self._format_value(value)}")

            elif isinstance(value, (list, dict)):
                count = len(value)

                if not count:
                    lines.append(
                        f"{field_prefix} {'[]' if isinstance(value, list) else '{}'}"
                    )
                    continue

                if not verbose or indent >= max_depth:
                    lines.append(f"{field_prefix} {self._format_value(value)}")
                    continue

                lines.append(field_prefix)

                items = list(value.items()) if isinstance(value, dict) else value

                for i, item in enumerate(items[:max_items]):
                    if isinstance(value, dict):
                        item_key, item_value = item
                    else:
                        item_key, item_value = None, item

                    item_prefix = "  " * (indent + 2)

                    if isinstance(item_value, Symbol):
                        label = f"{item_key!r}:" if item_key is not None else "-"

                        lines.append(f"{item_prefix}{label}")
                        lines.append(
                            item_value._format(
                                indent + 3,
                                seen,
                                verbose=True,
                                max_depth=max_depth,
                                max_items=max_items,
                            )
                        )
                    else:
                        label = f"{item_key!r}: " if item_key is not None else "- "
                        lines.append(
                            f"{item_prefix}{label}" f"{self._format_value(item_value)}"
                        )

                if count > max_items:
                    lines.append(f"{item_prefix}... +{count - max_items} more")

            else:
                lines.append(f"{field_prefix} {self._format_value(value)}")

        seen.remove(id(self))
        return "\n".join(lines)

    def __repr__(self):
        return self._format()

    def debug(self, *, max_depth=4, max_items=10):
        return self._format(
            verbose=True,
            max_depth=max_depth,
            max_items=max_items,
        )


@dataclass(slots=True, repr=False)
class AssignSymbol(Symbol):
    name: str
    value: Symbol | None

    field: FieldAccessSymbol | None = None
    parent_assign: AssignSymbol | None = None


@dataclass(slots=True, repr=False)
class DefinitionSymbol(AssignSymbol):
    pass


@dataclass(slots=True, repr=False)
class NumberSymbol(Symbol):
    value: int | float


@dataclass(slots=True, repr=False)
class StringSymbol(Symbol):
    value: str


@dataclass(slots=True, repr=False)
class NoneSymbol(Symbol):
    pass


@dataclass(slots=True, repr=False)
class FunctionSymbol(Symbol):
    name: str
    args: list[Symbol] = dc_field(default_factory=list)
    body: list[Symbol] = dc_field(default_factory=list)
    returned: list[Symbol] = dc_field(default_factory=list)
    is_called: bool = False


@dataclass(slots=True, repr=False)
class ReturnSymbol(Symbol):
    value: Symbol | None


@dataclass(slots=True, repr=False)
class CallSymbol(Symbol):
    name: str
    args: list[Symbol] = dc_field(default_factory=list)
    lookup: Symbol | None = None


@dataclass(slots=True, repr=False)
class IntrinsicCallSymbol(Symbol):
    name: str
    args: list[Symbol] = dc_field(default_factory=list)
    intrinsic: IntrinsicAST | None = None


@dataclass(slots=True, repr=False)
class VariableSymbol(Symbol):
    name: str
    lookup: Symbol


@dataclass(slots=True, repr=False)
class BinaryOpSymbol(Symbol):
    op: Symbol
    left_sym: Symbol
    right_sym: Symbol


@dataclass(slots=True, repr=False)
class UnaryOpSymbol(Symbol):
    op: Symbol
    right_sym: Symbol


@dataclass(slots=True, repr=False)
class ForSymbol(Symbol):
    pass
    # TODO: impl
    # def __init__(self, target, source, body, loop_count, ast_node):
    #     self.target = target
    #     self.source = source
    #     self.ast_node = ast_node
    #     self.body = body
    #     self.loop_count = loop_count

    #     self.type = None


@dataclass(slots=True, repr=False)
class UnavailableSymbol(Symbol):
    why: str


@dataclass(slots=True, repr=False)
class IfSymbol(Symbol):
    pass
    # TODO: impl
    # def __init__(
    #     self,
    #     cond,
    #     body,
    #     elifs,
    #     else_body,
    #     ast_node,
    #     body_scope,
    #     else_scope=None,
    #     merges=None,
    # ):
    #     self.cond = cond
    #     self.body = body
    #     self.body_scope = body_scope

    #     self.elifs = elifs
    #     self.else_body = else_body
    #     self.else_scope = else_scope

    #     self.ast_node = ast_node

    #     self.merges = merges


@dataclass(slots=True, repr=False)
class ElifSymbol(Symbol):
    pass
    # TODO: impl
    # def __init__(self, cond, body, ast_node, scope):
    #     self.cond = cond
    #     self.body = body
    #     self.scope = scope
    #     self.ast_node = ast_node


@dataclass(slots=True, repr=False)
class WhileSymbol(Symbol):
    pass
    # TODO: impl
    # def __init__(self, cond, body, ast_node):
    #     self.cond = cond
    #     self.body = body
    #     self.ast_node = ast_node


@dataclass(slots=True, repr=False)
class BooleanSymbol(Symbol):
    value: bool


@dataclass(slots=True, repr=False)
class ClassSymbol(Symbol):
    pass
    # TODO: impl
    # def __init__(self, name, ast_node):
    #     self.name = name
    #     self.ast_node = ast_node

    #     self.body = []

    #     self.init_fn = None
    #     self.params = None

    #     self.fields = {}
    #     self.field_syms = {}
    #     self.methods = {}

    #     self.method_syms = {}

    #     self.uses = []

    #     self.type = ClassType(name)


@dataclass(slots=True, repr=False)
class FieldAccessSymbol(Symbol):
    target: Symbol
    field: FieldAccessSymbol | None = None


@dataclass(slots=True, repr=False)
class SelfSymbol(Symbol):
    class_name: str | None = None


@dataclass(slots=True, repr=False)
class ConstructorCallSymbol(Symbol):
    pass
    # TODO: impl
    # def __init__(self, name, args, lookup, ast_node):
    #     self.name = name
    #     self.args = args
    #     self.lookup = lookup
    #     self.ast_node = ast_node

    #     self.arg_offset = 1

    #     self.type = None


@dataclass(slots=True, repr=False)
class ListLiteralSymbol(Symbol):
    pass
    # TODO: impl
    # def __init__(self, elements, ast_node):
    #     self.elements = elements
    #     self.appended_elements = []
    #     self.ast_node = ast_node

    #     self.type = None


@dataclass(slots=True, repr=False)
class MergeAssignmentSymbol(Symbol):
    merge_sym: AssignSymbol
    debug_name: str


@dataclass(slots=True, repr=False)
class IdentifierSymbol(Symbol):
    pass
    # TODO: impl
    # def __init__(self, name, ast_node):
    #     self.name = name
    #     self.ast_node = ast_node
    #     self.lookup = None
    #     self.field_name = None
    #     self.type = None
