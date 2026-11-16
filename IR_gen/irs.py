from dataclasses import dataclass, fields as dc_fields, field as dc_field, is_dataclass
from type_systems.types import *
from typing import Any


@dataclass(slots=True, kw_only=True, repr=False)
class IR:
    node_id: int = None
    type: Type = None

    @staticmethod
    def _is_symbol(value: Any) -> bool:
        return any(cls.__name__.endswith("Symbol") for cls in type(value).__mro__)

    @classmethod
    def _format_value(cls, value: Any) -> str:
        if value is None:
            return "None"

        if cls._is_symbol(value):
            return f"<NidaSym: {type(value).__name__}>"

        if isinstance(value, IR):
            return f"<{type(value).__name__}>"

        if isinstance(value, list):
            return "[" + ", ".join(cls._format_value(item) for item in value) + "]"

        if isinstance(value, tuple):
            content = ", ".join(cls._format_value(item) for item in value)
            if len(value) == 1:
                content += ","
            return f"({content})"

        if isinstance(value, dict):
            return (
                "{"
                + ", ".join(
                    f"{cls._format_value(k)}: {cls._format_value(v)}"
                    for k, v in value.items()
                )
                + "}"
            )

        return repr(value)

    def tree_repr(self, indent="", is_last=True):
        marker = "└── " if is_last else "├── "
        name = type(self).__name__

        fields = [
            field
            for field in dc_fields(self)
            if field.repr
            and field.name != "node_id"
            and not (field.name == "decs" and not getattr(self, field.name))
        ]

        # Leaf node: compact representation.
        if not any(
            isinstance(getattr(self, field.name), IR)
            or (
                isinstance(getattr(self, field.name), (list, tuple))
                and any(isinstance(item, IR) for item in getattr(self, field.name))
            )
            for field in fields
        ):
            args = ", ".join(
                f"{field.name}={self._format_value(getattr(self, field.name))}"
                for field in fields
            )
            return f"{indent}{marker}{name}({args})"

        lines = [f"{indent}{marker}{name}"]
        child_indent = indent + ("    " if is_last else "│   ")

        for i, field in enumerate(fields):
            value = getattr(self, field.name)
            last = i == len(fields) - 1

            if value is None:
                continue

            c_marker = "└── " if last else "├── "

            if isinstance(value, IR):
                lines.append(f"{child_indent}{c_marker}{field.name}:")
                lines.append(
                    value.tree_repr(
                        child_indent + ("    " if last else "│   "),
                        True,
                    )
                )

            elif isinstance(value, (list, tuple)) and any(
                isinstance(item, IR) for item in value
            ):
                lines.append(f"{child_indent}{c_marker}{field.name}:")
                list_indent = child_indent + ("    " if last else "│   ")

                for j, item in enumerate(value):
                    item_last = j == len(value) - 1

                    if isinstance(item, IR):
                        lines.append(item.tree_repr(list_indent, item_last))
                    else:
                        item_marker = "└── " if item_last else "├── "
                        lines.append(
                            f"{list_indent}{item_marker}" f"{self._format_value(item)}"
                        )

            else:
                lines.append(
                    f"{child_indent}{c_marker}{field.name}: "
                    f"{self._format_value(value)}"
                )

        return "\n".join(lines)

    def __repr__(self):
        return self.tree_repr()


@dataclass(slots=True, kw_only=True, repr=False)
class StmtIR(IR):
    pass


@dataclass(slots=True, kw_only=True, repr=False)
class ExprIR(IR):
    pass


# ---------------------
# ----- Statement -----
# ---------------------


@dataclass(slots=True, kw_only=True, repr=False)
class PassIR(StmtIR):
    pass


@dataclass(slots=True, kw_only=True, repr=False)
class AssignIR(StmtIR):
    name: str
    value: ExprIR = None
    re_assign: StmtIR = None
    field: ExprIR = None
    # def __init__(
    #     self,
    #     target,
    #     value,
    #     type=None,
    #     re_assign=False,
    #     field=None,
    # ):
    #     self.target = target
    #     self.value = value
    #     self.type = type

    #     self.re_assign = re_assign
    #     self.field = field


@dataclass(slots=True, kw_only=True, repr=False)
class FunctionIR(StmtIR):
    name: str
    args: list[AssignIR | SelfBoxIR] = dc_field(default_factory=list)
    body: list[StmtIR] = dc_field(default_factory=list)
    is_main_func: bool = False
    is_static: bool = False
    ast_name: str = None

    decorators: list[ExprIR] = dc_field(default_factory=list)

    # def __init__(
    #     self,
    #     decs,
    #     name,
    #     args,
    #     body,
    #     type=None,
    #     is_main_func=False,
    #     is_static=False,
    #     ast_name=None,
    # ):
    #     self.decs = decs
    #     self.name = name
    #     self.args = args
    #     self.body = body
    #     self.type = type

    #     self.is_static = is_static

    #     self.is_main_func = is_main_func

    #     # The name in the source, before it was turned into an id.
    #     self.ast_name = ast_name


@dataclass(slots=True, kw_only=True, repr=False)
class ReturnIR(StmtIR):
    value: ExprIR

    # def __init__(self, value, type=None):
    #     self.value = value
    #     self.type = None


@dataclass(slots=True, kw_only=True, repr=False)
class ClassIR(StmtIR):
    name: str
    body: list[StmtIR] = dc_field(default_factory=list)
    fields: list[tuple] = dc_field(default_factory=list)

    # def __init__(self, name, id, body, fields=None):
    #     self.name = name
    #     self.body = body

    #     # The declared fields of the class: [(name, type, default_value)].
    #     self.fields = fields or []


@dataclass(slots=True, kw_only=True, repr=False)
class IRImport(StmtIR):
    pass
    # TODO: impl
    # def __init__(
    #     self,
    #     module: str,
    #     symbols: list[str] = None,
    #     alias: str = None,
    #     resolved_module=None,
    # ):
    #     self.module = module
    #     self.symbols = symbols or []
    #     self.alias = alias
    #     self.resolved_module = resolved_module


@dataclass(slots=True, kw_only=True, repr=False)
class IfIR(StmtIR):
    cond: ExprIR
    body: list[StmtIR] = dc_field(default_factory=list)
    elifs: list[ElifIR] = dc_field(default_factory=list)
    else_body: BlockIR = None
    if_sym: IfIR = None

    # def __init__(self, cond, body, elifs, else_body, if_sym):
    #     self.cond = cond
    #     self.body = body
    #     self.elifs = elifs
    #     self.else_body = else_body
    #     self.if_sym = if_sym


@dataclass(slots=True, kw_only=True, repr=False)
class ElifIR(StmtIR):
    cond: ExprIR
    body: list[StmtIR] = dc_field(default_factory=list)
    # def __init__(self, cond, body):
    #     self.cond = cond
    #     self.body = body


@dataclass(slots=True, kw_only=True, repr=False)
class BlockIR(StmtIR):
    body: list[StmtIR] = dc_field(default_factory=list)
    # def __init__(self, body):
    #     self.body = body


@dataclass(slots=True, kw_only=True, repr=False)
class ForIR(StmtIR):
    target: str
    source: ExprIR
    body: list[StmtIR] = dc_field(default_factory=list)
    # def __init__(self, target, source, body):
    #     self.target = target
    #     self.source = source
    #     self.body = body


@dataclass(slots=True, kw_only=True, repr=False)
class WhileIR(StmtIR):
    cond: ExprIR
    body: list[StmtIR] = dc_field(default_factory=list)
    # def __init__(self, cond, body):
    #     self.cond = cond
    #     self.body = body


@dataclass(slots=True, kw_only=True, repr=False)
class DefinitionIR(StmtIR):
    name: str
    value: ExprIR = None
    initializer: StmtIR = None

    # def __init__(self, target, value, type):
    #     self.target = target
    #     self.value = value
    #     self.type = type

    #     self.initializer = None


@dataclass(slots=True, kw_only=True, repr=False)  # only use for ir_passer
class StructIR(StmtIR):
    name: str
    fields: list[AssignIR] = dc_field(default_factory=list)
    class_fields: list[tuple] = dc_field(default_factory=list)
    initialize_function: FunctionIR = None
    # def __init__(self, name, fields: list[AssignIR], class_fields=None):
    #     self.name = name
    #     self.fields = fields

    #     # The physical layout of the struct: [(name, type, default_value)].
    #     self.class_fields = class_fields or []

    #     self.initialize_function = None


# ---------------------
# ---- Expression -----
# ---------------------


@dataclass(slots=True, kw_only=True, repr=False)
class StringLiteralIR(ExprIR):
    value: str
    # def __init__(self, value):
    #     self.value = value


@dataclass(slots=True, kw_only=True, repr=False)
class RangeIR(ExprIR):
    pass
    # TODO: impl
    # def __init__(self, start, end, step):
    #     self.start = start
    #     self.end = end
    #     self.step = step


@dataclass(slots=True, kw_only=True, repr=False)
class NoneIR(ExprIR):
    air: bool = True
    # def __init__(self, air=True):
    #     self.air = air


@dataclass(slots=True, kw_only=True, repr=False)
class IntrinsicCallIR(ExprIR):
    intrinsic: Any
    name: str
    args: list[ExprIR]

    # def __init__(self, intrinsic, name, args, type):
    #     self.intrinsic = intrinsic
    #     self.name = name
    #     self.args = args
    #     self.type = type


@dataclass(slots=True, kw_only=True, repr=False)
class BooleanIR(ExprIR):
    value: bool
    # def __init__(self, value):
    #     self.value = value


@dataclass(slots=True, kw_only=True, repr=False)
class GroupIR(ExprIR):
    expr: ExprIR
    # def __init__(self, expr):
    #     self.expr = expr


@dataclass(slots=True, kw_only=True, repr=False)
class NewIR(ExprIR):
    class_name: str

    """Allocates an instance of a class."""

    # def __init__(self, class_name, type=None):
    #     self.class_name = class_name
    #     self.type = type


@dataclass(slots=True, kw_only=True, repr=False)
class BinaryOpIR(ExprIR):
    left: ExprIR
    right: ExprIR
    op: str
    # def __init__(self, left, right, op, type=None):
    #     self.left = left
    #     self.right = right
    #     self.op = op
    #     self.type = type


@dataclass(slots=True, kw_only=True, repr=False)
class VariableIR(ExprIR):
    name: str
    receiver: ExprIR = None

    # def __init__(self, name, type=None):
    #     self.name = name
    #     self.type = type

    #     self.target = name


@dataclass(slots=True, kw_only=True, repr=False)
class CallIR(ExprIR):
    name: str
    args: list[ExprIR]
    field: ExprIR = None
    runtime_call: bool = False

    # def __init__(self, target, args, type=None, field=None):
    #     self.target = target
    #     self.args = args
    #     self.type = type

    #     self.field = field

    #     self.imported_func_call = False

    #     self.runtime_call = False


@dataclass(slots=True, kw_only=True, repr=False)
class NumberIR(ExprIR):
    value: int
    # def __init__(self, value, type=None):
    #     self.value = value
    #     self.type = type


@dataclass(slots=True, kw_only=True, repr=False)
class FieldAccessIR(ExprIR):
    target: ExprIR
    field: str

    # def __init__(self, target, field, type=None):
    #     self.target = target
    #     self.field = field
    #     self.type = type


@dataclass(slots=True, kw_only=True, repr=False)
class UnaryOpIR(ExprIR):
    value: ExprIR
    op: str

    # def __init__(self, op, value, type=None):
    #     self.op = op
    #     self.value = value
    #     self.type = type


@dataclass(slots=True, kw_only=True, repr=False)
class ListLiteralIR(ExprIR):
    pass
    # TODO: impl
    # def __init__(self, elements, type=None):
    #     self.elements = elements
    #     self.type = type


@dataclass(slots=True, kw_only=True, repr=False)
class IdentifierIR(ExprIR):
    name: str
    # def __init__(self, name):
    #     self.name = name


@dataclass(slots=True, kw_only=True, repr=False)
class SelfBoxIR(ExprIR):
    ir: ExprIR
    # def __init__(self, ir):
    #     self.ir = ir
