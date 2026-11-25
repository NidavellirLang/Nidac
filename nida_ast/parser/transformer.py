from .lark_loader import LarkLoader
from ..base import *
from .parse_nodes import *
from utils.errors import *

Token = LarkLoader.Token
Tree = LarkLoader.Tree


class ASTTranslator(LarkLoader.Transformer):
    def __init__(self, id_alloc=None, source=None, **kwargs):
        super().__init__(**kwargs)
        self.id_alloc = id_alloc
        self.source = source

    # ---------------------
    # ------ Helpers ------
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

    def name(self, children):
        return children[0]

    def var_target(self, children):
        token = children[0]

        return IdentifierAST(
            name=str(token),
            node_id=self.alloc_id(),
            line=self._token_line(token),
        )

    def member_name(self, children):
        return self.var_target(children)

    def var_ref(self, children):
        token = children[0]

        return VariableAST(
            name=str(token),
            node_id=self.alloc_id(),
            line=self._token_line(token),
        )

    def _build_target(self, target):
        if isinstance(target, Tree):
            return self.visit(target)

        return target

    def arguments(self, children):
        return list(children)

    def _create(self, cls, start, end=None, **kwargs):
        return cls(
            **kwargs,
            node_id=self.alloc_id(),
            line=(
                self._span_line(start, end)
                if end is not None
                else self._get_line(start)
            ),
        )

    def _line(self, start, end=None):
        if end is None:
            return self._get_line(start)

        return self._span_line(start, end)

    def call(self, children):
        target = children[0]
        arguments = children[1] if len(children) > 1 else []

        end = arguments[-1] if arguments else target

        return self._create(
            CallAST,
            target,
            end,
            target=target,
            arguments=arguments,
        )

    def func_name(self, children):
        token = children[0]

        return IdentifierAST(
            name=str(token),
            node_id=self.alloc_id(),
            line=self._token_line(token),
        )

    def type_spec(self, children):
        type = children[0].children[0]
        return Type(value=str(type), line=self._line(type))

    def func_args(self, children):
        return FuncArgs(list(children))

    def param_name(self, children):
        return children[0]

    def _create_func_param(self, args):
        formatted_args = []
        for arg in args:
            child = arg.children
            if len(child) == 2:
                type, name = child
            elif len(child) == 1:
                name = child[0]
                type = None
            else:
                raise NidavellirSyntaxError(
                    "Invalid function argument", self._get_line(arg)
                )

            identifier = self._create(IdentifierAST, name, name=str(name))
            formatted_args.append(
                self._create(
                    AssignAST,
                    identifier,
                    type,
                    target=identifier,
                    value=None,
                    type=type.value if type is not None else None,
                )
            )

        return formatted_args

    def suite(self, children):
        return Body(children)

    def function_def(self, children):
        return_type = None
        name = None
        args = []
        body = []

        for child in children:
            if isinstance(child, FuncArgs):
                args = child.values
            elif isinstance(child, IdentifierAST):
                name = child
            elif isinstance(child, Type):
                return_type = child
            elif isinstance(child, Body):
                body = child.body

        args = self._create_func_param(args)

        if name is None:
            raise NidavellirSyntaxError(
                "Function name is missing",
                self._get_line(children[0]),
            )

        return FunctionAST(
            name=name,
            body=body,
            args=args,
            type=return_type.value if return_type is not None else None,
        )

    def attr_access(self, children):
        return self._create(
            FieldAccessAST,
            children[0],
            children[1],
            target=children[0],
            access=children[1],
        )

    def pass_stmt(self, children):
        return self._create(PassAST, start=children[0])

    def assignment_suffix(self, children):
        return children[1]

    def assignment(self, children):
        if len(children) == 2:
            target, value = children
            type = None
        elif len(children) == 3:
            type_node, target, value = children
            type = self._type_format(type_node)
        else:
            line = self._get_line(children[0]) if children else None
            raise NidavellirSyntaxError(
                f"Invalid assignment structure: expected 2 or 3 children, got {len(children)}",
                line,
            )

        return self._create(
            AssignAST,
            target,
            value,
            target=target,
            value=value,
            type=type,
        )
