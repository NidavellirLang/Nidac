from __future__ import annotations

from dataclasses import dataclass, fields, field
from utils.errors import Line
from utils.tree_utils import TreeReprMixin, _paint, _CYAN, _MAGENTA


from typing import Any


@dataclass(slots=True, repr=False, kw_only=True)
class AST(TreeReprMixin):
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


@dataclass(slots=True, repr=False)
class FunctionAST(AST):
    name: str | int
    args: list
    body: list
    type: str = None
    decorators: list = field(default_factory=list)
    is_imported: bool = False


@dataclass(slots=True, repr=False)
class BlockAST(AST):
    body: list


@dataclass(slots=True, repr=False)
class ElifAST(AST):
    cond: AST
    body: list


@dataclass(slots=True, repr=False)
class ElseAST(AST):
    body: list


@dataclass(slots=True, repr=False)
class IfAST(AST):
    cond: AST
    body: list
    elifs: list
    elses: ElseAST | None


@dataclass(slots=True, repr=False)
class NumberAST(AST):
    value: int | float


@dataclass(slots=True, repr=False)
class StringAST(AST):
    value: str


@dataclass(slots=True, repr=False)
class VariableAST(AST):
    name: str


@dataclass(slots=True, repr=False)
class IndexAccessAST(AST):
    target: AST
    index: AST


@dataclass(slots=True, repr=False)
class CallAST(AST):
    target: IdentifierAST | FieldAccessAST
    arguments: list


@dataclass(slots=True, repr=False)
class ReturnAST(AST):
    value: AST


@dataclass(slots=True, repr=False)
class AssignAST(AST):
    target: IdentifierAST | FieldAccessAST
    value: AST | None
    type: str | None


@dataclass(slots=True, repr=False)
class DefinitionAST(AST):
    target: str
    value: AST
    type: str


@dataclass(slots=True, repr=False)
class DeclareAST(AST):
    target: IdentifierAST | FieldAccessAST
    type: str | None


@dataclass(slots=True, repr=False)
class WhileAST(AST):
    cond: AST
    body: list


@dataclass(slots=True, repr=False)
class ForAST(AST):
    target: DeclareAST
    source: AST
    body: list


@dataclass(slots=True, repr=False)
class PassAST(AST):
    pass


@dataclass(slots=True, repr=False)
class BinaryOpAST(AST):
    left: AST
    op: str
    right: AST


@dataclass(slots=True, repr=False)
class BooleanAST(AST):
    value: bool


@dataclass(slots=True, repr=False)
class ClassAST(AST):
    name: IdentifierAST
    body: list
    decorators: list


@dataclass(slots=True, repr=False)
class UnaryOpAST(AST):
    op: str
    right: AST


@dataclass(slots=True, repr=False)
class DecoratorAST(AST):
    name: str
    args: list


@dataclass(slots=True, repr=False)
class FieldAccessAST(AST):
    target: AST
    access: IdentifierAST


@dataclass(slots=True, repr=False)
class ListLiteralAST(AST):
    elements: list


@dataclass(slots=True, repr=False)
class IntrinsicAST(AST):
    name: str
    params: Any
    type: Any


@dataclass(slots=True, repr=False)
class IntrinsicCallAST(AST):
    intrinsic: IntrinsicAST
    name: str
    arguments: list


@dataclass(slots=True, repr=False)
class ImportAST(AST):
    module: str
    symbols: list
    alias: str


@dataclass(slots=True, repr=False)
class NoneAST(AST):
    pass


@dataclass(slots=True)
class IdentifierAST(AST):
    name: str


class BreakAST(AST):
    pass


class ContinueAST(AST):
    pass
