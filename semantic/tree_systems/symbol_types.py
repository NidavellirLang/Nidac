from __future__ import annotations

from type_systems.types import Type
from utils import SysArgs
import traceback

# from dataclasses import dataclass, fields, field as dc_field
from dataclasses import dataclass, fields as dc_fields, field as dc_field, is_dataclass
from nida_ast.base import AST, IntrinsicAST


class TrackedList(list):
    def _log(self, operation, *args):
        print(
            f"\n[USES {operation}]"
            f"\n  OWNER: {getattr(self, 'owner', None)!r}"
            f"\n  ARGS: {args!r}",
            flush=True,
        )
        traceback.print_stack()

    def append(self, item):
        self._log("APPEND", item)
        super().append(item)

    def extend(self, items):
        items = list(items)
        self._log("EXTEND", items)
        super().extend(items)

    def insert(self, index, item):
        self._log("INSERT", index, item)
        super().insert(index, item)

    def __iadd__(self, items):
        self._log("IADD", items)
        return super().__iadd__(items)

    def __setitem__(self, key, value):
        self._log("SETITEM", key, value)
        super().__setitem__(key, value)


@dataclass(slots=True, repr=False, kw_only=True)
class Symbol:
    type: Type | None = None
    ast_node: AST | None = None
    if SysArgs.log_uses_appends:
        uses: list["Symbol"] = dc_field(default_factory=TrackedList)
    else:
        uses: list["Symbol"] = dc_field(default_factory=list)

    _FORMAT_SKIP = {"ast_node"}
    _FORMAT_MAX_ITEMS = 5
    _FORMAT_MAX_DEPTH = 2
    _FORMAT_MAX_VALUE_LEN = 100

    def __setattr__(self, name, value):

        if name in SysArgs.log_set_sym_attr:
            try:
                old_value = object.__getattribute__(self, name)
            except AttributeError:
                old_value = "<UNSET>"

            print(
                f"\n[SYM ATTR WRITE] {type(self).__name__}.{name}"
                f"\n  SYMBOL: {getattr(self, 'name', '<UNSET>')}"
                f"\n  OLD: {old_value!r}"
                f"\n  NEW: {value!r}",
                flush=True,
            )

            traceback.print_stack()

        object.__setattr__(self, name, value)

    @staticmethod
    def _symbol_ref(value):
        cls = type(value).__name__

        name = getattr(value, "name", None)
        if name is None:
            name = getattr(value, "value", None)

        symbol_type = getattr(value, "type", None)

        parts = [cls]

        if name is not None:
            parts.append(repr(name))

        if symbol_type is not None:
            parts.append(f"type={type(symbol_type).__name__}")

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

        if is_dataclass(value) and not isinstance(value, type):
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
            field.name: getattr(self, field.name)
            for field in dc_fields(self)
            if not field.name.startswith("_") and field.name not in self._FORMAT_SKIP
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
                    empty = "[]" if isinstance(value, list) else "{}"
                    lines.append(f"{field_prefix} {empty}")
                    continue

                if not verbose or indent >= max_depth:
                    lines.append(f"{field_prefix} {self._format_value(value)}")
                    continue

                lines.append(field_prefix)

                items = list(value.items()) if isinstance(value, dict) else value

                for item in items[:max_items]:
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
    class_ref_type: Type | None = None
    args: list[Symbol] = dc_field(default_factory=list)
    field: FieldAccessSymbol | None = None
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
    cond: Symbol
    body: list[Symbol]
    elifs: list[ElifSymbol] = dc_field(default_factory=list)
    else_body: list[Symbol] | None = None
    merges: list[MergeAssignmentSymbol] = dc_field(default_factory=list)


@dataclass(slots=True, repr=False)
class ElifSymbol(Symbol):
    cond: Symbol
    body: list[Symbol] = dc_field(default_factory=list)

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
    name: str
    init_fn: FunctionSymbol | None = None
    params: list[Symbol] = dc_field(default_factory=list)
    body: list[Symbol] = dc_field(default_factory=list)
    fields: dict[str, Symbol] = dc_field(default_factory=dict)
    methods: dict[str, Symbol] = dc_field(default_factory=dict)
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
    name: str = "self"


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
    name: str
    lookup: Symbol | None = None
    resolve_name: str | None = None
    pass
    # TODO: impl
    # def __init__(self, name, ast_node):
    #     self.name = name
    #     self.ast_node = ast_node
    #     self.lookup = None
    #     self.field_name = None
    #     self.type = None
