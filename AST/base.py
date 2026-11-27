from __future__ import annotations

from dataclasses import dataclass, fields, field
from utils.errors import Line
from utils.tree_utils import TreeReprMixin, _paint, _CYAN, _MAGENTA


from typing import Any

from utils.traversal import Child  # noqa: F401  (part of the AST node DSL)


@dataclass(slots=True, repr=False, kw_only=True)
class AST(TreeReprMixin):
    __scope__ = False
    __children__ = ()

    line: Line = None
    node_id: int = None

    @classmethod
    def _is_line(cls, value: Any) -> bool:
        return isinstance(value, Line)

    @classmethod
    def _tree_format_value(cls, value: Any) -> str:
        if cls._is_line(value):
            return (
                f"{_paint('Line', _CYAN)}("
                f"{_paint(str(value.line), _MAGENTA)}, "
                f"{_paint(str(value.col_start), _MAGENTA)}, "
                f"{_paint(str(value.col_end), _MAGENTA)})"
            )

        return TreeReprMixin._tree_format_value(value)


@dataclass(slots=True, repr=False, kw_only=True)
class StmtAST(AST):
    pass


@dataclass(slots=True, repr=False, kw_only=True)
class ExprAST(AST):
    pass


# ---------------------
# ----- Statement -----
# ---------------------


class BreakAST(StmtAST):
    pass


class ContinueAST(StmtAST):
    pass


@dataclass(slots=True, repr=False, kw_only=True)
class ImportAST(StmtAST):
    module: str
    symbols: list
    alias: str


@dataclass(slots=True, repr=False, kw_only=True)
class ClassAST(StmtAST):
    __scope__ = True
    __children__ = ("name", "body")

    name: IdentifierAST
    body: list
    decorators: list


@dataclass(slots=True, repr=False, kw_only=True)
class ReturnAST(StmtAST):
    __children__ = (Child("value", optional=True),)

    value: ExprAST | None


@dataclass(slots=True, repr=False, kw_only=True)
class AssignAST(StmtAST):
    __children__ = ("target", "value")

    target: IdentifierAST | FieldAccessAST
    value: ExprAST
    type: str | None


@dataclass(slots=True, repr=False, kw_only=True)
class DefinitionAST(StmtAST):
    __children__ = ("target", "value")

    target: IdentifierAST
    value: ExprAST
    type: str


@dataclass(slots=True, repr=False, kw_only=True)
class DeclareAST(StmtAST):
    __children__ = ("target",)

    target: IdentifierAST | FieldAccessAST
    type: str | None


@dataclass(slots=True, repr=False, kw_only=True)
class WhileAST(StmtAST):
    __scope__ = True
    __children__ = ("cond", "body")

    cond: ExprAST
    body: list


@dataclass(slots=True, repr=False, kw_only=True)
class ForAST(StmtAST):
    __scope__ = True
    __children__ = ("target", "source", "body")

    target: DeclareAST
    source: ExprAST
    body: list


@dataclass(slots=True, repr=False, kw_only=True)
class PassAST(StmtAST):
    pass


@dataclass(slots=True, repr=False, kw_only=True)
class FunctionAST(StmtAST):
    __scope__ = True
    __children__ = ("name", "args", "body")

    name: IdentifierAST
    args: list
    body: list
    type: str = None
    decorators: list = field(default_factory=list)


@dataclass(slots=True, repr=False, kw_only=True)
class BlockAST(StmtAST):
    __children__ = ("body",)

    body: list


@dataclass(slots=True, repr=False, kw_only=True)
class ElifAST(StmtAST):
    __scope__ = True
    __children__ = ("cond", "body")

    cond: ExprAST
    body: list


@dataclass(slots=True, repr=False, kw_only=True)
class ElseAST(StmtAST):
    __scope__ = True
    __children__ = ("body",)

    body: list


@dataclass(slots=True, repr=False, kw_only=True)
class IfAST(StmtAST):
    __scope__ = True
    __children__ = (
        "cond",
        "body",
        Child("elifs", optional=True),
        Child("elses", optional=True),
    )

    cond: ExprAST
    body: list[StmtAST]
    elifs: list[StmtAST]
    elses: ElseAST | None


# ---------------------
# ---- Expression -----
# ---------------------


@dataclass(slots=True, repr=False, kw_only=True)
class NumberAST(ExprAST):
    value: int | float


@dataclass(slots=True, repr=False, kw_only=True)
class StringAST(ExprAST):
    value: str


@dataclass(slots=True, repr=False, kw_only=True)
class VariableAST(ExprAST):
    name: str


@dataclass(slots=True, repr=False, kw_only=True)
class IndexAccessAST(ExprAST):
    __children__ = ("target", "index")

    target: ExprAST
    index: ExprAST


@dataclass(slots=True, repr=False, kw_only=True)
class CallAST(ExprAST):
    __children__ = ("target", "arguments")

    target: IdentifierAST | FieldAccessAST
    arguments: list


@dataclass(slots=True, repr=False, kw_only=True)
class BinaryOpAST(ExprAST):
    __children__ = ("left", "right")

    left: ExprAST
    op: str
    right: ExprAST


@dataclass(slots=True, repr=False, kw_only=True)
class BooleanAST(ExprAST):
    value: bool


@dataclass(slots=True, repr=False, kw_only=True)
class UnaryOpAST(ExprAST):
    __children__ = ("right",)

    op: str
    right: ExprAST


@dataclass(slots=True, repr=False, kw_only=True)
class DecoratorAST(AST):
    name: str
    args: list


@dataclass(slots=True, repr=False, kw_only=True)
class FieldAccessAST(ExprAST):
    __children__ = ("target", "access")

    target: ExprAST
    access: IdentifierAST


@dataclass(slots=True, repr=False, kw_only=True)
class ListLiteralAST(ExprAST):
    elements: list


@dataclass(slots=True, repr=False, kw_only=True)
class IntrinsicAST(ExprAST):
    name: str
    params: Any
    type: Any


@dataclass(slots=True, repr=False, kw_only=True)
class IntrinsicCallAST(ExprAST):
    __children__ = ("name", "arguments")

    intrinsic: IntrinsicAST
    name: IdentifierAST
    arguments: list


@dataclass(slots=True, repr=False, kw_only=True)
class NoneAST(ExprAST):
    pass


@dataclass(slots=True)
class IdentifierAST(ExprAST):
    name: str
