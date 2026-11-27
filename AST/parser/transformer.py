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
        return self._create(NumberAST, token, value=int(token))

    def STRING(self, token):
        return self._create(StringAST, token, value=str(token))

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
                    DeclareAST,
                    type or identifier,
                    identifier,
                    target=identifier,
                    type=type.value if type is not None else None,
                )
            )

        return formatted_args

    def suite(self, children):
        return Body(children)

    def for_stmt(self, children):
        if isinstance(children[0], Type):
            type, target, _, source, body = children
        else:
            target, _, source, body = children
            type = None

        formatted_target = self._create(
            DeclareAST,
            target,
            target=target,
            type=type.value if type is not None else None,
        )

        return self._create(
            ForAST,
            formatted_target,
            body.body[-1],
            target=formatted_target,
            source=source,
            body=body.body,
        )

    def return_stmt(self, children):
        if len(children) == 1:
            return self._create(ReturnAST, start=children[0], value=None)
        elif len(children) == 2:
            return self._create(
                ReturnAST, start=children[0], end=children[1], value=children[1]
            )
        else:
            raise NidavellirSyntaxError(
                "Invalid return statement", self._get_line(children[0])
            )

    def break_stmt(self, children):
        return self._create(BreakAST, start=children[0])

    def continue_stmt(self, children):
        return self._create(ContinueAST, start=children[0])

    def else_clause(self, children):
        body = children[0]
        return self._create(
            ElseAST,
            body.body[-1],
            body=body.body,
        )

    def elif_clause(self, children):
        cond = children[0]
        body = children[1]
        return self._create(ElifAST, cond, body.body[-1], cond=cond, body=body.body)

    def if_stmt(self, children):
        cond = children[0]
        body = children[1]
        elifs = []
        elses = None

        for child in children[2:]:
            if isinstance(child, ElifAST):
                elifs.append(child)
            elif isinstance(child, ElseAST):
                if elses is not None:
                    raise NidavellirSyntaxError(
                        "Multiple else clauses", self._get_line(child)
                    )

                elses = child
            else:
                raise NidavellirSyntaxError(f"Invalid if statement {child}")

        return self._create(
            IfAST,
            cond,
            body.body[-1],
            cond=cond,
            body=body.body,
            elifs=elifs,
            elses=elses,
        )

    def _binary_op(self, children):
        left, op, right = children
        return self._create(
            BinaryOpAST,
            left,
            right,
            left=left,
            right=right,
            op=str(op),
        )

    def or_expr(self, children):
        return self._binary_op(children)

    def and_expr(self, children):
        return self._binary_op(children)

    def sum_expr(self, children):
        return self._binary_op(children)

    def comparison(self, children):
        return self._binary_op(children)

    def comparison_op(self, children):
        if len(children) == 1:
            return str(children[0])
        elif len(children) == 2:
            return str(children[0] + " " + children[1])
        else:
            raise NidavellirSyntaxError(
                "Invalid comparison operator", self._get_line(children[0])
            )

    def unary_op(self, children):
        op, left = children
        return self._create(
            UnaryOpAST,
            op,
            left,
            right=left,
            op=str(op),
        )

    def logical_not(self, children):
        return self.unary_op(children)

    def term(self, children):
        return self._binary_op(children)

    def _boolean(self, start, value: bool):
        return self._create(BooleanAST, start=start, value=value)

    def true(self, children):
        return self._boolean(children[0], True)

    def false(self, children):
        return self._boolean(children[0], False)

    def none(self, children):
        return self._create(NoneAST, start=children[0])

    def while_stmt(self, children):
        cond, body = children
        return self._create(
            WhileAST,
            cond,
            body.body[-1],
            cond=cond,
            body=body.body,
        )

    def class_name(self, children):
        return children[0]

    def _name_to_identifier(self, token):
        return self._create(
            IdentifierAST,
            token,
            name=str(token),
        )

    def class_def(self, children):
        name, body = children
        return self._create(
            ClassAST,
            start=name,
            end=body.body[-1],
            name=self._name_to_identifier(name),
            body=body.body,
            decorators=None,
        )

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

        return self._create(
            FunctionAST,
            start=return_type or name,
            end=body[-1],
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

    def var_decl_name(self, children):
        name = children[0]
        return self._create(
            IdentifierAST,
            name,
            name=str(name),
        )

    def declaration(self, children):
        type, name = children
        return self._create(
            DeclareAST,
            type,
            name,
            type=type.value,
            target=name,
        )

    def assignment_suffix(self, children):
        return children[1]

    def assignment(self, children):
        if len(children) == 2:
            target, value = children
            type = None
        elif len(children) == 3:
            type_node, target, value = children
            type = type_node.value
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
