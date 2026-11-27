from __future__ import annotations

from type_systems.types import Type
from utils import SysArgs
import traceback

# from dataclasses import dataclass, fields, field as dc_field
from dataclasses import dataclass, fields as dc_fields, field as dc_field, is_dataclass
from AST.base import AST, IntrinsicAST
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .before_type_engine.symbol_tree.symbol_table import Scope


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


@dataclass(frozen=True, slots=True)
class Child:
    name: str
    optional: bool = False


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

    @property
    def node_id(self):
        ast_node = self.ast_node
        if ast_node:
            return ast_node.node_id


@dataclass(slots=True, repr=False, kw_only=True)
class AssignSymbol(Symbol):
    __children__ = ("target", Child("value", optional=True))

    target: IdentifierSymbol | FieldAccessSymbol
    value: Symbol | None

    parent_assign: AssignSymbol | None = None


@dataclass(slots=True, repr=False, kw_only=True)
class DefinitionSymbol(AssignSymbol):
    pass


@dataclass(slots=True, repr=False, kw_only=True)
class NumberSymbol(Symbol):
    value: int | float


@dataclass(slots=True, repr=False, kw_only=True)
class StringSymbol(Symbol):
    value: str


@dataclass(slots=True, repr=False, kw_only=True)
class NoneSymbol(Symbol):
    pass


@dataclass(slots=True, repr=False, kw_only=True)
class FunctionSymbol(Symbol):
    __children__ = ("name", "args", "body")

    name: IdentifierSymbol
    args: list[Symbol] = dc_field(default_factory=list)
    body: list[Symbol] = dc_field(default_factory=list)
    returned: list[Symbol] = dc_field(default_factory=list)
    is_called: bool = False

    scope: Scope = None


@dataclass(slots=True, repr=False, kw_only=True)
class ReturnSymbol(Symbol):
    __children__ = (Child("value", optional=True),)

    value: Symbol | None


@dataclass(slots=True, repr=False, kw_only=True)
class CallSymbol(Symbol):
    __children__ = ("target", "arguments")

    target: IdentifierSymbol | FieldAccessSymbol

    arguments: list[Symbol] = dc_field(default_factory=list)
    lookup: Symbol | None = None


@dataclass(slots=True, repr=False, kw_only=True)
class IntrinsicCallSymbol(Symbol):
    __children__ = ("target", "arguments")

    name: IdentifierSymbol
    args: list[Symbol] = dc_field(default_factory=list)
    intrinsic: IntrinsicAST | None = None


@dataclass(slots=True, repr=False, kw_only=True)
class VariableSymbol(Symbol):
    __children__ = ("name", "lookup")

    name: IdentifierSymbol
    lookup: Symbol


@dataclass(slots=True, repr=False, kw_only=True)
class BinaryOpSymbol(Symbol):
    __children__ = ("left", "right")

    op: Symbol
    left: Symbol
    right: Symbol


@dataclass(slots=True, repr=False, kw_only=True)
class UnaryOpSymbol(Symbol):
    __children__ = ("right",)

    op: Symbol
    right: Symbol


@dataclass(slots=True, repr=False, kw_only=True)
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


@dataclass(slots=True, repr=False, kw_only=True)
class UnavailableSymbol(Symbol):
    why: str


@dataclass(slots=True, repr=False, kw_only=True)
class IfSymbol(Symbol):
    __children__ = ("cond", "body", "elifs", Child("elses", optional=True), "merges")

    cond: Symbol
    body: list[Symbol]
    elifs: list[ElifSymbol] = dc_field(default_factory=list)
    elses: list[Symbol] | None = None
    merges: list[MergeAssignmentSymbol] = dc_field(default_factory=list)


@dataclass(slots=True, repr=False, kw_only=True)
class ElifSymbol(Symbol):
    __children__ = ("cond", "body")

    cond: Symbol
    body: list[Symbol] = dc_field(default_factory=list)


@dataclass(slots=True, repr=False, kw_only=True)
class WhileSymbol(Symbol):
    __children__ = ("cond", "body")

    cond: Symbol
    body: list[Symbol] = dc_field(default_factory=list)


@dataclass(slots=True, repr=False, kw_only=True)
class BooleanSymbol(Symbol):
    value: bool


@dataclass(slots=True, repr=False, kw_only=True)
class ClassSymbol(Symbol):
    __children__ = ("name", "init_fn", "params", "body")

    name: IdentifierSymbol
    init_fn: FunctionSymbol | None = None
    params: list[Symbol] = dc_field(default_factory=list)
    body: list[Symbol] = dc_field(default_factory=list)
    fields: dict[str, Symbol] = dc_field(default_factory=dict)
    methods: dict[str, Symbol] = dc_field(default_factory=dict)


@dataclass(slots=True, repr=False, kw_only=True)
class FieldAccessSymbol(Symbol):
    __children__ = ("target", Child("field", optional=True))

    target: Symbol
    field: FieldAccessSymbol | None = None


@dataclass(slots=True, repr=False, kw_only=True)
class MergeAssignmentSymbol(Symbol):
    __children__ = ("merge_sym",)

    merge_sym: AssignSymbol
    debug_name: str


@dataclass(slots=True, repr=False, kw_only=True)
class IdentifierSymbol(Symbol):
    name: str
    lookup: Symbol | None = None
    resolve_name: str | None = None


@dataclass(slots=True, repr=False, kw_only=True)
class BreakSymbol(Symbol):
    pass


@dataclass(slots=True, repr=False, kw_only=True)
class ContinueSymbol(Symbol):
    pass


class PassSymbol(Symbol):
    pass


@dataclass(slots=True, repr=False, kw_only=True)
class IndexAccessSymbol(Symbol):
    target: VariableSymbol
    index: Symbol
