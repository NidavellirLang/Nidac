from .lark_loader import LarkLoader
from ..base import *
from utils.errors import *

Token = LarkLoader.Token


class ASTTranslator(LarkLoader.Transformer):
    def __init__(self, id_alloc=None, source=None, **kwargs):
        super().__init__(**kwargs)
        self.id_alloc = id_alloc
        self.source = source

    # ---------------------
    # ------ Heplers ------
    # ---------------------

    def alloc_id(self):
        return self.id_alloc.alloc()

    def _get_line(self, node):
        if isinstance(node, Token):
            return self._token_line(node)

        if not hasattr(node, "line"):
            raise TypeError(f"Expected AST node, got {type(node).__name__}: {node!r}")

        return node.line

    def _token_line(self, token):
        if isinstance(token, AST):
            return token.line

        return Line(
            source=self.source,
            line=token.line,
            col_start=token.column - 1,
            col_end=token.end_column - 1,
        )

    def _span_line(self, start, end):
        start_line = self._get_line(start)
        end_line = self._get_line(end)

        return Line(
            source=self.source,
            line=start_line.line,
            col_start=start_line.col_start,
            col_end=end_line.col_end,
        )

    # ---------------------
    # ----- Transforms ----
    # ---------------------

    def start(self, children):
        return children

    def expr(self, children):
        return children[0]

    def NUMBER(self, token):
        return NumberAST(
            int(token),
            node_id=self.alloc_id(),
            line=self._token_line(token),
        )

    def access(self, children):
        if len(children) == 1:
            return IdentifierAST(
                name=str(children[0]),
                node_id=self.alloc_id(),
                line=self._token_line(children[0]),
            )

        return FieldAccessAST(
            target=children[0],
            field=IdentifierAST(
                name=str(children[1]),
                node_id=self.alloc_id(),
                line=self._token_line(children[0]),
            ),
            line=self._token_line(children[0]),
        )

    def typed_access(self, children):
        if len(children) == 1:
            return None, children[0]

        return children[0], children[1]

    def arithmetic_op(self, children):
        return str(children[0])

    def term_op(self, children):
        return str(children[0])

    def arithmetic(self, children):
        if len(children) == 1:
            return children[0]

        left, operator, right = children

        return BinaryOpAST(
            left=left,
            op=str(operator),
            right=right,
            node_id=self.alloc_id(),
            line=self._span_line(left, right),
        )

    def term(self, children):
        if len(children) == 1:
            return children[0]

        left, operator, right = children

        return BinaryOpAST(
            left=left,
            operator=str(operator),
            right=right,
            node_id=self.alloc_id(),
            line=self._span_line(left, right),
        )

    def call_args(self, children):
        return children

    def call(self, children):
        target = children[0]
        args = children[1] if len(children) > 1 else []

        return CallAST(
            target=target,
            args=args,
            node_id=self.alloc_id(),
            line=self._span_line(target, args[-1] if args else target),
        )

    def assignment(self, children):
        # TODO: impl operator
        typed_access, operator, value = children

        type_name, target = typed_access

        if type_name is not None:
            type_name = str(type_name)

        return AssignAST(
            target=target,
            value=value,
            type=type_name,
            node_id=self.alloc_id(),
            line=self._span_line(typed_access[0] or target, value),
        )

    def simple_stmt(self, children):
        return children[0]
