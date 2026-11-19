from dataclasses import dataclass, field as dc_field
from type_systems.types import *
from typing import Any, ClassVar

from utils.tree_utils import TreeReprMixin, _paint, _YELLOW


@dataclass(frozen=True, slots=True)
class Child:
    name: str
    optional: bool = False


@dataclass(slots=True, kw_only=True, repr=False)
class IR(TreeReprMixin):
    __child__: ClassVar[tuple[str | Child, ...]] = ()

    _tree_skip_fields = ("node_id",)

    node_id: int = None
    type: Type = None

    @staticmethod
    def _is_symbol(value: Any) -> bool:
        return any(cls.__name__.endswith("Symbol") for cls in type(value).__mro__)

    @classmethod
    def _tree_is_node(cls, value: Any) -> bool:
        return isinstance(value, IR)

    @classmethod
    def _tree_format_value(cls, value: Any) -> str:
        if cls._is_symbol(value):
            return _paint(f"<NidaSym: {type(value).__name__}>", _YELLOW)

        return TreeReprMixin._tree_format_value(value)


@dataclass(slots=True, kw_only=True, repr=False)
class StmtIR(IR):
    pass


@dataclass(slots=True, kw_only=True, repr=False)
class ExprIR(IR):
    pass


@dataclass(slots=True, kw_only=True, repr=False)
class ParameterIR(IR):
    __child__ = (Child("default", optional=True),)

    name: str
    type: Type
    default: ExprIR = None


@dataclass(slots=True, kw_only=True, repr=False)
class FieldDeclIR(IR):
    __child__ = (Child("default", optional=True),)

    name: str
    type: Type
    default: ExprIR | None = None


# ---------------------
# ----- Statement -----
# ---------------------


@dataclass(slots=True, kw_only=True, repr=False)
class PassIR(StmtIR):
    pass


@dataclass(slots=True, kw_only=True, repr=False)
class EliminatedIR(StmtIR):
    pass


class BreakIR(StmtIR):
    pass


@dataclass(slots=True, kw_only=True, repr=False)
class AssignIR(StmtIR):
    __child__ = ("value", "target")

    target: IdentifierIR | FieldAccessIR
    value: ExprIR = None
    re_assign: bool = False

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
    __child__ = ("args", "body", "decorators")

    name: str
    args: list[AssignIR] = dc_field(default_factory=list)
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
    __child__ = ("value",)

    value: ExprIR

    # def __init__(self, value, type=None):
    #     self.value = value
    #     self.type = None


@dataclass(slots=True, kw_only=True, repr=False)
class ClassIR(StmtIR):
    __child__ = ("body", "fields")

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
    __child__ = ("cond", "body", "elifs", Child("else_body", optional=True))

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
    __child__ = ("cond", "body")

    cond: ExprIR
    body: list[StmtIR] = dc_field(default_factory=list)
    # def __init__(self, cond, body):
    #     self.cond = cond
    #     self.body = body


@dataclass(slots=True, kw_only=True, repr=False)
class BlockIR(StmtIR):
    __child__ = ("body",)

    body: list[StmtIR] = dc_field(default_factory=list)
    # def __init__(self, body):
    #     self.body = body


@dataclass(slots=True, kw_only=True, repr=False)
class ForIR(StmtIR):
    __child__ = ("source", "body")

    target: str
    source: ExprIR
    body: list[StmtIR] = dc_field(default_factory=list)
    # def __init__(self, target, source, body):
    #     self.target = target
    #     self.source = source
    #     self.body = body


@dataclass(slots=True, kw_only=True, repr=False)
class WhileIR(StmtIR):
    __child__ = ("cond", "body")

    cond: ExprIR
    body: list[StmtIR] = dc_field(default_factory=list)
    # def __init__(self, cond, body):
    #     self.cond = cond
    #     self.body = body


@dataclass(slots=True, kw_only=True, repr=False)
class DefinitionIR(StmtIR):
    __child__ = (Child("value", optional=True),)

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
    __child__ = ("fields", Child("initialize_function", optional=True))

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


@dataclass(slots=True, kw_only=True, repr=False)
class StmtExprIR(StmtIR):
    __child__ = ("expr",)

    expr: ExprIR


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
    __child__ = ("target", "args")

    intrinsic: Any
    target: IdentifierIR | FieldAccessIR
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
    __child__ = ("expr",)

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
    __child__ = ("left", "right")

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
    __child__ = (Child("receiver", optional=True),)

    name: str
    receiver: ExprIR = None

    # def __init__(self, name, type=None):
    #     self.name = name
    #     self.type = type

    #     self.target = name


@dataclass(slots=True, kw_only=True, repr=False)
class FunctionRefIR(ExprIR):
    name: str


@dataclass(slots=True, kw_only=True, repr=False)
class BoundMethodIR(ExprIR):
    __child__ = ("receiver",)

    receiver: ExprIR
    method: str


@dataclass(slots=True, kw_only=True, repr=False)
class BoundCallIR(ExprIR):
    __child__ = ("bound", "args")

    bound: ExprIR
    args: list[ExprIR] = dc_field(default_factory=list)
    ref: Type = None


@dataclass(slots=True, kw_only=True, repr=False)
class CallIR(ExprIR):
    __child__ = ("target", "args")

    target: IdentifierIR | FieldAccessIR
    args: list[ExprIR]
    runtime_call: bool = False
    indirect: bool = False

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
    __child__ = ("target",)

    target: ExprIR
    field: str

    # def __init__(self, target, field, type=None):
    #     self.target = target
    #     self.field = field
    #     self.type = type


@dataclass(slots=True, kw_only=True, repr=False)
class UnaryOpIR(ExprIR):
    __child__ = ("value",)

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
class IndexAccessIR(ExprIR):
    __child__ = ("target", "index")

    target: VariableIR
    index: ExprIR
