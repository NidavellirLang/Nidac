from dataclasses import dataclass, fields, field
from utils.errors import Line


@dataclass(slots=True, repr=False, kw_only=True)
class AST:
    line: Line = None
    node_id: int = None

    def _format(self, indent=0):
        lines = []
        prefix = "  " * indent
        class_name = type(self).__name__

        attrs = {
            f.name: getattr(self, f.name)
            for f in fields(self)
            if not f.name.startswith("_")
        }

        if not attrs:
            return f"{prefix}{class_name}()"

        lines.append(f"{prefix}{class_name}:")

        for key, value in attrs.items():
            field_prefix = f"{prefix}  {key}:"

            if isinstance(value, AST):
                lines.append(field_prefix)
                lines.append(value._format(indent + 2))

            elif isinstance(value, list):
                if not value:
                    lines.append(f"{field_prefix} []")
                    continue

                lines.append(field_prefix)

                for item in value:
                    if isinstance(item, AST):
                        lines.append(f"{prefix}    -")
                        lines.append(item._format(indent + 3))

                    elif isinstance(item, list):
                        if not item:
                            lines.append(f"{prefix}    - []")

                        for sub_item in item:
                            if isinstance(sub_item, AST):
                                lines.append(f"{prefix}    -")
                                lines.append(sub_item._format(indent + 3))
                            else:
                                lines.append(f"{prefix}    - {sub_item!r}")

                    else:
                        lines.append(f"{prefix}    - {item!r}")

            elif value is None:
                lines.append(f"{field_prefix} None")

            else:
                lines.append(f"{field_prefix} {value!r}")

        return "\n".join(lines)

    def __repr__(self):
        return self._format()


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
class IfAST(AST):
    cond: AST
    body: list
    elifs: list
    else_body: list


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
    target: str
    chain: list
    args: list


@dataclass(slots=True, repr=False)
class ReturnAST(AST):
    value: AST


@dataclass(slots=True, repr=False)
class AssignAST(AST):
    target: str
    chain: list
    value: AST
    type: str


@dataclass(slots=True, repr=False)
class DefinitionAST(AST):
    target: str
    value: AST
    type: str


@dataclass(slots=True, repr=False)
class WhileAST(AST):
    cond: AST
    body: list


@dataclass(slots=True, repr=False)
class ForAST(AST):
    target: AST
    source: AST
    body: list


@dataclass(slots=True, repr=False)
class ListAST(AST):
    body: list


@dataclass(slots=True, repr=False)
class OperatorAST(AST):
    op: str


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
    name: str
    body: list
    decorators: list


@dataclass(slots=True, repr=False)
class SelfAST(AST):
    pass


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
    field: IdentifierAST


@dataclass(slots=True, repr=False)
class ListLiteralAST(AST):
    elements: list


@dataclass(slots=True, repr=False)
class IntrinsicAST(AST):
    name: str
    params: list
    handler: str
    type: str


@dataclass(slots=True, repr=False)
class IntrinsicCallAST(AST):
    intrinsic: IntrinsicAST
    name: str
    args: list


@dataclass(slots=True, repr=False)
class ImportAST(AST):
    module: str
    symbols: list
    alias: str


@dataclass(slots=True, repr=False)
class GroupAST(AST):
    expr: AST


@dataclass(slots=True, repr=False)
class NoneAST(AST):
    pass


@dataclass(slots=True)
class IdentifierAST(AST):
    name: str
