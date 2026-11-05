from .base import *
from .keys import create_keywords, ASSIGN_TOKENS, COMPOUND_MAP
import inspect
from utils.errors import NidavellirSyntaxError, Line


class Parser:
    def __init__(self, lexer, ctx):
        self.id_alloc = ctx["id_alloc"]

        self.tokens = lexer.tokenize()
        self.lines = lexer.sp
        self.index = 0
        self.asts = []
        self.last_decorators = []
        self.keywords = create_keywords(self)

        # print(self.tokens)

    def get_token(self, index):
        if 0 <= index < len(self.tokens):
            return self.tokens[index]
        return None

    @property
    def current(self):
        return self.get_token(self.index)

    def _col_of(self, token, from_col=None):
        """Best-effort 1-based start column of `token` on its source line.

        Tokens only carry (kind, value, line), so the column is recovered by
        locating the token text inside the source line. Returns None when the
        token has no text (NEWLINE/INDENT/DEDENT) or cannot be located.
        """
        if token is None or len(token) < 3:
            return None

        line_num = token[2]
        value = token[1]

        if value is None or not line_num or not (1 <= line_num <= len(self.lines)):
            return None

        text = self.lines[line_num - 1]
        offset = 0 if from_col is None else max(0, from_col - 1)
        idx = text.find(str(value), offset)

        return (idx + 1) if idx >= 0 else None

    def _make_line(self, start_token=None, end_token=None):
        """Build a Line spanning start_token (where the node began) to
        end_token (last token consumed for it)."""
        if start_token is None:
            start_token = self.current
        if start_token is None:
            return Line(self.lines, 1, 1, 1)

        line_num = start_token[2] if len(start_token) > 2 and start_token[2] else 1
        col_start = self._col_of(start_token) or 1

        end_line = None
        if end_token is not None and len(end_token) > 2:
            end_line = end_token[2]

        if end_token is not None and end_line == line_num and end_token[1] is not None:
            end_col = self._col_of(end_token, col_start)
            col_end = (
                end_col + len(str(end_token[1]))
                if end_col is not None
                else col_start + 1
            )
        elif end_token is None and start_token[1] is not None:
            # Single token: the range is exactly that token's text.
            col_end = col_start + len(str(start_token[1]))
        elif 1 <= line_num <= len(self.lines):
            # Multi-line or unknown end: cover the rest of the start line.
            col_end = max(col_start + 1, len(self.lines[line_num - 1]) + 1)
        else:
            col_end = col_start + 1

        return Line(self.lines, line_num, col_start, col_end)

    def _span_line(self, left_line, right_line, fallback_token=None):
        """Line covering `left_line`'s start through `right_line`'s end.

        Used for compound nodes (binary/unary/postfix) so the range spans the
        whole expression rather than just the operator token. Falls back to the
        operator token when the operands are not usable.
        """
        if left_line is None or right_line is None:
            return self._make_line(fallback_token)

        if left_line.line != right_line.line:
            # Cross-line expression: cover from left start to end of its line.
            start = self._line_num(fallback_token, left_line.line)
            return Line(
                self.lines,
                left_line.line,
                left_line.col_start,
                max(left_line.col_start + 1, len(self.lines[left_line.line - 1]) + 1),
            )

        return Line(self.lines, left_line.line, left_line.col_start, right_line.col_end)

    def _current_line(self):
        """Get Line object for current token."""
        return self._make_line(self.current)

    def _block_line(self, start_token, end_token=None):
        """Line for a statement whose body is an indented block (def/if/
        while/for/class/else/elif).

        `Line` describes a single source line, so such a statement is anchored
        at its first line (`def foo(...):`) and the column range covers the
        rest of that line.
        """
        line = self._make_line(start_token)
        if 1 <= line.line <= len(self.lines):
            line.col_end = max(line.col_start + 1, len(self.lines[line.line - 1]) + 1)
        return line

    def print_error(self, msg):
        curr = self.current
        if curr is None:
            raise NidavellirSyntaxError(
                "Unexpected end of file", Line(self.lines, 1, 1, 1)
            )

        raise NidavellirSyntaxError(msg, self._current_line())

    def advance(self):
        token = self.current
        self.index += 1
        return token

    def peek_kind(self):
        curr = self.current
        if curr is None:
            return None
        return curr[0] if isinstance(curr, tuple) else curr

    def peek_kind_at(self, offset=0):
        tok = self.get_token(self.index + offset)
        if tok is None:
            return None
        return tok[0] if isinstance(tok, tuple) else tok

    def consume(self, kind):
        if self.peek_kind() == kind:
            return self.advance()

        self.print_error("Syntax Error")

    def parse_number(self, data_type=None):
        token_value = self.advance()
        line = self._make_line(token_value)
        return NumberAST(
            value=token_value[1],
            type=data_type,
            line=line,
            node_id=self.id_alloc.alloc(),
        )

    def check_index_access(self):
        start_index = self.index
        find_name = False
        find_bracket = False

        if self.peek_kind() != "LBRACKET":
            self.index = start_index
            return False

        self.index -= 1
        if self.peek_kind() == "NAME":
            self.index = start_index
            find_name = True

        if find_name:
            find_bracket = 0
            while self.current is not None:
                if self.peek_kind() == "LBRACKET":
                    find_bracket += 1
                elif self.peek_kind() == "RBRACKET":
                    find_bracket -= 1

                if find_bracket == 0:
                    break

                self.advance()

            if self.peek_kind() == "RBRACKET":
                self.index = start_index
                find_bracket = True

            if find_bracket and find_name:
                self.index = start_index
                return True

        self.index = start_index

        return False

    def parse_list_literal(self):
        index_access = self.check_index_access()

        start_token = self.current
        self.consume("LBRACKET")
        elements = []

        if self.peek_kind() != "RBRACKET":
            while self.current is not None:
                elements.append(self.parse_expression())

                if self.peek_kind() == "COMMA":
                    self.advance()
                else:
                    break

        end_token = self.current
        self.consume("RBRACKET")
        line = self._make_line(start_token, end_token)

        if index_access:
            return IndexAccessAST(
                target=None, index=elements[0], line=line, node_id=self.id_alloc.alloc()
            )
        else:
            return ListLiteralAST(
                elements=elements, line=line, node_id=self.id_alloc.alloc()
            )

    def parse_primary(self):
        kind = self.peek_kind()

        if kind == "NUMBER":
            token = self.advance()
            line = self._make_line(token)
            return NumberAST(value=token[1], line=line, node_id=self.id_alloc.alloc())

        if kind == "STRING":
            token = self.advance()
            line = self._make_line(token)
            return StringAST(value=token[1], line=line, node_id=self.id_alloc.alloc())

        if kind == "NAME":
            return self.parse_name()

        if kind == "LBRACKET":
            return self.parse_list_literal()

        if kind == "LPAREN":
            start_token = self.current
            self.advance()
            expr = self.parse_expression()
            end_token = self.current
            self.consume("RPAREN")
            line = self._make_line(start_token, end_token)
            return GroupAST(expr, line=line, node_id=self.id_alloc.alloc())

        if kind == "TRUE":
            token = self.advance()
            line = self._make_line(token)
            return BooleanAST(True, line=line, node_id=self.id_alloc.alloc())

        if kind == "FALSE":
            token = self.advance()
            line = self._make_line(token)
            return BooleanAST(False, line=line, node_id=self.id_alloc.alloc())

        if kind == "NONE":
            token = self.advance()
            line = self._make_line(token)
            return NoneAST(line=line, node_id=self.id_alloc.alloc())

        self.print_error(f"Unexpected token in expression")

    def parse_postfix(self):
        left = self.parse_primary()

        while True:
            kind = self.peek_kind()

            if kind == "DOT":
                self.advance()
                member_token = self.consume("NAME")

                field = IdentifierAST(
                    name=member_token[1],
                    line=self._make_line(member_token),
                    node_id=self.id_alloc.alloc(),
                )

                line = self._span_line(left.line, field.line, member_token)

                left = FieldAccessAST(
                    target=left,
                    field=field,
                    line=line,
                    node_id=self.id_alloc.alloc(),
                )

            elif kind == "LBRACKET":
                self.advance()
                index_expr = self.parse_expression()
                end_token = self.current
                self.consume("RBRACKET")
                line = self._span_line(
                    left.line, self._make_line(index_expr.line or end_token), end_token
                )
                left = IndexAccessAST(
                    target=left,
                    index=index_expr,
                    line=line,
                    node_id=self.id_alloc.alloc(),
                )

            elif kind == "LPAREN":
                self.advance()
                args = self.parse_args()
                end_token = self.current
                self.consume("RPAREN")
                last = args[-1].line if args and args[-1] is not None else None
                start_line = left.line or self._make_line(end_token)
                end_line = last or self._make_line(end_token)
                line = self._span_line(start_line, end_line, end_token)
                left = CallAST(
                    target=left, args=args, line=line, node_id=self.id_alloc.alloc()
                )

            else:
                break

        return left

    def _binary_line(self, left, right, op_token):
        """Range of a binary op spanning both operands."""
        if left is not None and left.line is not None:
            return self._span_line(
                left.line, right.line if right is not None else None, op_token
            )
        return self._make_line(op_token)

    def parse_unary(self):
        kind = self.peek_kind()

        if kind in ("MINUS", "PLUS"):
            op_token = self.advance()
            right = self.parse_unary()
            line = self._span_line(
                self._make_line(op_token),
                right.line if right is not None else None,
                op_token,
            )
            return UnaryOpAST(
                op=op_token[1], right=right, line=line, node_id=self.id_alloc.alloc()
            )

        return self.parse_postfix()

    def parse_factor(self):
        left = self.parse_unary()

        while self.peek_kind() in ("STAR", "DIV"):
            op_token = self.advance()
            right = self.parse_unary()
            left = BinaryOpAST(
                left=left,
                op=op_token[1],
                right=right,
                line=self._binary_line(left, right, op_token),
                node_id=self.id_alloc.alloc(),
            )

        return left

    def parse_or(self):
        left = self.parse_and()

        while self.peek_kind() in ("OR"):
            op_token = self.advance()
            right = self.parse_and()
            left = BinaryOpAST(
                left=left,
                op=op_token[1],
                right=right,
                line=self._binary_line(left, right, op_token),
                node_id=self.id_alloc.alloc(),
            )

        return left

    def parse_and(self):
        left = self.parse_equality()

        while self.peek_kind() in ("AND"):
            op_token = self.advance()
            right = self.parse_equality()
            left = BinaryOpAST(
                left=left,
                op=op_token[1],
                right=right,
                line=self._binary_line(left, right, op_token),
                node_id=self.id_alloc.alloc(),
            )

        return left

    def parse_term(self):
        left = self.parse_factor()

        while self.peek_kind() in ("PLUS", "MINUS"):
            op_token = self.advance()
            right = self.parse_factor()
            left = BinaryOpAST(
                left=left,
                op=op_token[1],
                right=right,
                line=self._binary_line(left, right, op_token),
                node_id=self.id_alloc.alloc(),
            )

        return left

    def parse_equality(self):
        left = self.parse_term()

        while True:
            kind = self.peek_kind()

            if kind in ("EQEQ", "NEQ", "GT", "LT", "GTE", "LTE"):
                op_token = self.advance()
                right = self.parse_term()
                left = BinaryOpAST(
                    left=left,
                    op=op_token[1],
                    right=right,
                    line=self._binary_line(left, right, op_token),
                    node_id=self.id_alloc.alloc(),
                )

            elif (
                kind == "IS"
                and self.peek_kind_at(1) == "NOT"
                and self.peek_kind_at(2) == "IN"
            ):
                op_token = self.current
                self.advance()  # is
                self.advance()  # not
                self.advance()  # in
                right = self.parse_term()
                left = BinaryOpAST(
                    left=left,
                    op="is not in",
                    right=right,
                    line=self._binary_line(left, right, op_token),
                    node_id=self.id_alloc.alloc(),
                )

            elif kind == "IS" and self.peek_kind_at(1) == "NOT":
                op_token = self.current
                self.advance()  # is
                self.advance()  # not
                right = self.parse_term()
                left = BinaryOpAST(
                    left=left,
                    op="is not",
                    right=right,
                    line=self._binary_line(left, right, op_token),
                    node_id=self.id_alloc.alloc(),
                )

            elif kind == "IS":
                op_token = self.advance()  # is
                right = self.parse_term()
                left = BinaryOpAST(
                    left=left,
                    op="is",
                    right=right,
                    line=self._binary_line(left, right, op_token),
                    node_id=self.id_alloc.alloc(),
                )

            elif kind == "NOT" and self.peek_kind_at(1) == "IN":
                op_token = self.current
                self.advance()  # not
                self.advance()  # in
                right = self.parse_term()
                left = BinaryOpAST(
                    left=left,
                    op="not in",
                    right=right,
                    line=self._binary_line(left, right, op_token),
                    node_id=self.id_alloc.alloc(),
                )

            elif kind == "IN":
                op_token = self.advance()  # in
                right = self.parse_term()
                left = BinaryOpAST(
                    left=left,
                    op="in",
                    right=right,
                    line=self._binary_line(left, right, op_token),
                    node_id=self.id_alloc.alloc(),
                )

            else:
                break

        return left

    def parse_expression(self):
        return self.parse_or()

    def parse_chain_target(self):
        start_token = self.consume("NAME")
        target_name = start_token[1]

        target = VariableAST(
            name=target_name,
            line=self._make_line(start_token),
            node_id=self.id_alloc.alloc(),
        )

        has_access = False

        while True:
            kind = self.peek_kind()

            if kind == "DOT":
                self.advance()
                member_token = self.consume("NAME")

                field = IdentifierAST(
                    name=member_token[1],
                    line=self._make_line(member_token),
                    node_id=self.id_alloc.alloc(),
                )

                target = FieldAccessAST(
                    target=target,
                    field=field,
                    line=self._span_line(target.line, field.line, member_token),
                    node_id=self.id_alloc.alloc(),
                )

                has_access = True

            elif kind == "LBRACKET":
                self.advance()
                index_expr = self.parse_expression()
                end_token = self.current
                self.consume("RBRACKET")

                target = IndexAccessAST(
                    target=target,
                    index=index_expr,
                    line=self._span_line(
                        target.line, self._make_line(end_token), end_token
                    ),
                    node_id=self.id_alloc.alloc(),
                )

                has_access = True

            else:
                break

        return target_name, target if has_access else None

    def check_function_call(self):
        start_index = self.index

        if self.peek_kind() != "NAME":
            return False

        self.advance()

        while self.peek_kind() == "DOT":
            self.advance()
            if self.peek_kind() == "NAME":
                self.advance()

        if self.peek_kind() != "LPAREN":
            self.index = start_index
            return False

        find_lparen = False
        is_func = False

        while self.current is not None:
            kind = self.peek_kind()

            if kind == "LPAREN":
                find_lparen = True

            if kind == "RPAREN":
                if find_lparen:
                    is_func = True
                break

            if kind == "NEWLINE" and not find_lparen:
                break

            self.advance()

        self.index = start_index
        return is_func

    def check_assignment(self):
        offset = 0
        paren_depth = 0
        bracket_depth = 0
        brace_depth = 0

        prev_kind = None

        while True:
            tok = self.get_token(self.index + offset)
            if tok is None:
                break

            kind = tok[0] if isinstance(tok, tuple) else tok

            if kind == "LPAREN":
                paren_depth += 1
            elif kind == "RPAREN":
                paren_depth -= 1
            elif kind == "LBRACKET":
                bracket_depth += 1
            elif kind == "RBRACKET":
                bracket_depth -= 1
            elif kind == "LBRACE":
                brace_depth += 1
            elif kind == "RBRACE":
                brace_depth -= 1

            if kind in ("NEWLINE", "DEDENT"):
                break

            if paren_depth == 0 and bracket_depth == 0 and brace_depth == 0:
                if kind == "COMMA":
                    return False

                if kind in ASSIGN_TOKENS:
                    return True

                if prev_kind == "NAME" and kind == "NAME":
                    # "NAME NAME" is a typed declaration ("def int x = 5"),
                    # but "def int name(" is a function signature.
                    nxt = self.get_token(self.index + offset + 1)
                    nxt_kind = nxt[0] if isinstance(nxt, tuple) else nxt
                    if nxt_kind == "LPAREN":
                        return False
                    return True

            prev_kind = kind
            offset += 1

        return False

    def skip_newlines(self):
        while self.current is not None and self.peek_kind() == "NEWLINE":
            self.advance()

    def parse_decorator(self):
        if self.peek_kind() != "AT":
            return False

        self.advance()
        decorators = []
        while self.current is not None and self.peek_kind() == "NAME":
            start_token = self.current
            decorator_name = self.advance()[1]

            args = []

            if self.peek_kind() == "LPAREN":
                self.advance()
                self.skip_newlines()
                while self.current is not None and self.peek_kind() != "RPAREN":
                    arg = self.parse_expression()
                    if arg is not None:
                        args.append(arg)
                    else:
                        self.print_error("Syntax Error: Expected argument")

                    self.skip_newlines()

                self.consume("RPAREN")

            end_token = self.current
            line = self._make_line(start_token, end_token)

            if self.peek_kind() == "COMMA":
                self.advance()

            decorators.append(
                DecoratorAST(
                    decorator_name, args, line=line, node_id=self.id_alloc.alloc()
                )
            )

        return decorators

    def get_compound_assignment(self):
        start_index = self.index

        while self.peek_kind() is not None and self.peek_kind() not in ASSIGN_TOKENS:
            if self.peek_kind() == "NEWLINE":
                self.index = start_index
                return False

            self.advance()

        if self.peek_kind() in ASSIGN_TOKENS and self.peek_kind() != "ASSIGN":
            r = COMPOUND_MAP[self.peek_kind()]
            self.index = start_index
            return r

        self.index = start_index
        return False

    def parse_type(self):
        start_index = self.index
        if self.peek_kind() != "NAME":
            return None

        type_name = self.advance()[1]

        while self.peek_kind() == "STAR":
            self.advance()
            type_name += "*"  # example "char*", "int**"

        if self.peek_kind() != "NAME":
            self.index = start_index
            return None

        return type_name

    def parse_assignment(self, is_definition=False):
        start_token = self.current
        type = self.parse_type()

        comp = self.get_compound_assignment()
        target_name, field = self.parse_chain_target()

        data_type = type

        if data_type and field is not None:
            self.print_error(
                f"Syntax Error: Cannot use type annotation '{data_type}' "
                f"on member access '{target_name}'.\n"
                f"  --> Fields already have a type defined in their class."
            )

        if self.peek_kind() == "COLON":
            self.print_error("Syntax Error: Unexpected ':'")

        value_ast = None

        if self.peek_kind() in ASSIGN_TOKENS:
            op_token = self.consume(self.peek_kind())
            value_ast = self.parse_expression()

            if comp:
                op_line = self._make_line(op_token)

                target_ast = (
                    field
                    if field is not None
                    else VariableAST(
                        name=target_name,
                        line=op_line,
                        node_id=self.id_alloc.alloc(),
                    )
                )

                value_ast = BinaryOpAST(
                    left=target_ast,
                    op=comp,
                    right=value_ast,
                    line=op_line,
                    node_id=self.id_alloc.alloc(),
                )

        end_token = self.current
        line = self._make_line(start_token, end_token)

        if is_definition:
            if field is not None:
                self.print_error(
                    f"Syntax Error: Cannot use type annotation '{data_type}' "
                    f"on member access '{target_name}'.\n"
                    f"  --> Fields already have a type defined in their class."
                )

            return DefinitionAST(
                target=target_name,
                type=data_type,
                value=value_ast,
                line=line,
                node_id=self.id_alloc.alloc(),
            )

        return AssignAST(
            target=target_name,
            field=field,
            type=data_type,
            value=value_ast,
            line=line,
            node_id=self.id_alloc.alloc(),
        )

    def parse_args(self):
        args = []
        while self.current is not None and self.peek_kind() != "RPAREN":
            arg_ast = self.parse_expression()
            if arg_ast is not None:
                args.append(arg_ast)

            if self.peek_kind() == "COMMA":
                self.advance()

        return args

    def parse_function_call(self):
        start_token = self.current
        target_name, chain = self.parse_chain_target()

        self.consume("LPAREN")

        args = self.parse_args()

        end_token = self.current
        self.consume("RPAREN")
        line = self._make_line(start_token, end_token)

        return CallAST(
            target=target_name,
            field=chain,
            args=args,
            line=line,
            node_id=self.id_alloc.alloc(),
        )

    def parse_name(self, is_func_arg=False):
        token = self.current
        if token is None:
            self.print_error("Syntax Error: Expected name")

        if self.check_assignment():
            return self.parse_assignment()
        elif self.check_function_call():
            return self.parse_function_call()
        elif token[1] == "self":
            self.advance()
            line = self._make_line(token)
            return SelfAST(line=line, node_id=self.id_alloc.alloc())
        elif is_func_arg:
            return self.parse_assignment()
        else:
            self.advance()
            line = self._make_line(token)
            return VariableAST(name=token[1], line=line, node_id=self.id_alloc.alloc())

    def parse_else(self):
        start_token = self.current
        self.consume("ELSE")
        self.consume("COLON")
        self.consume("NEWLINE")
        self.consume("INDENT")

        body = []
        while self.current is not None and self.peek_kind() != "DEDENT":
            kind = self.parse_kind(self.peek_kind())
            if kind is not None:
                body.append(kind)
            else:
                self.advance()

        end_token = self.current
        self.consume("DEDENT")
        line = self._block_line(start_token, end_token)
        return BlockAST(body, line=line, node_id=self.id_alloc.alloc())

    def parse_elif(self):
        start_token = self.current
        self.consume("ELIF")
        cond = self.parse_expression()

        self.consume("COLON")
        self.consume("NEWLINE")
        self.consume("INDENT")

        body = []
        while self.current is not None and self.peek_kind() != "DEDENT":
            kind = self.parse_kind(self.peek_kind())
            if kind is not None:
                body.append(kind)
            else:
                self.advance()

        end_token = self.current
        self.consume("DEDENT")
        line = self._block_line(start_token, end_token)

        return ElifAST(cond, body, line=line, node_id=self.id_alloc.alloc())

    def parse_if(self):
        start_token = self.current
        self.consume("IF")
        cond = self.parse_expression()

        self.consume("COLON")
        self.consume("NEWLINE")
        self.consume("INDENT")
        body = []
        while self.current is not None and self.peek_kind() != "DEDENT":
            kind = self.parse_kind(self.peek_kind())
            if kind is not None:
                body.append(kind)
            else:
                self.advance()

        self.consume("DEDENT")

        self.skip_newlines()

        elifs = []
        while self.current is not None and self.peek_kind() == "ELIF":
            elifs.append(self.parse_elif())
            self.skip_newlines()

        else_body = None
        if self.current is not None and self.peek_kind() == "ELSE":
            else_body = self.parse_else()

        end_token = self.current
        line = self._block_line(start_token, end_token)

        return IfAST(
            cond, body, elifs, else_body, line=line, node_id=self.id_alloc.alloc()
        )

    def parse_def(self, decorators=None):
        start_token = self.current
        self.consume("DEF")
        if decorators:
            self.last_decorators = []

        ch = self.check_assignment()
        if ch:
            assignment = self.parse_assignment(is_definition=True)
            return assignment

        start = self.consume("NAME")

        name = None
        type = None

        if self.peek_kind() == "NAME":
            type = start[1]
            name = self.advance()
        elif self.peek_kind() == "LPAREN":
            name = start
        else:
            self.print_error("Syntax Error: Expected function name")

        self.consume("LPAREN")

        args = []
        while self.current is not None and self.peek_kind() == "NAME":
            args.append(self.parse_name(is_func_arg=True))
            if self.peek_kind() == "COMMA":
                self.advance()

        self.consume("RPAREN")
        self.consume("COLON")
        self.consume("NEWLINE")
        self.consume("INDENT")

        body = []
        while self.current is not None and self.peek_kind() != "DEDENT":
            kind = self.parse_kind(self.peek_kind())
            if kind is not None:
                body.append(kind)
            else:
                self.advance()

        end_token = self.current
        self.consume("DEDENT")
        line = self._block_line(start_token, end_token)

        return FunctionAST(
            name=name[1],
            args=args,
            body=body,
            type=type,
            decorators=decorators,
            line=line,
            node_id=self.id_alloc.alloc(),
        )

    def parse_return(self):
        start_token = self.current
        self.consume("RETURN")
        value = None
        if self.peek_kind() != "NEWLINE":
            value = self.parse_expression()
        if value is not None and value.line is not None:
            line = self._span_line(
                self._make_line(start_token), value.line, start_token
            )
        else:
            line = self._make_line(start_token)
        return ReturnAST(value, line=line, node_id=self.id_alloc.alloc())

    def parse_class(self, decorators=None):
        start_token = self.current
        if decorators:
            self.last_decorators = []

        self.consume("CLASS")
        name = self.consume("NAME")
        self.consume("COLON")
        self.consume("NEWLINE")
        self.consume("INDENT")

        body = []
        while self.current is not None and self.peek_kind() != "DEDENT":
            kind = self.parse_kind(self.peek_kind())
            if kind is not None:
                body.append(kind)
            else:
                self.advance()

        end_token = self.current
        self.consume("DEDENT")
        line = self._block_line(start_token, end_token)
        return ClassAST(
            name=name[1],
            body=body,
            decorators=decorators,
            line=line,
            node_id=self.id_alloc.alloc(),
        )

    def parse_while(self):
        start_token = self.current
        self.consume("WHILE")
        cond = self.parse_expression()
        self.consume("COLON")
        self.consume("NEWLINE")
        self.consume("INDENT")

        body = []
        while self.current is not None and self.peek_kind() != "DEDENT":
            kind = self.parse_kind(self.peek_kind())
            if kind is not None:
                body.append(kind)
            else:
                self.advance()

        end_token = self.current
        self.consume("DEDENT")
        line = self._block_line(start_token, end_token)

        return WhileAST(cond, body, line=line, node_id=self.id_alloc.alloc())

    def parse_for(self):
        start_token = self.current
        self.consume("FOR")

        target = self.parse_assignment()

        self.consume("IN")
        source = self.parse_expression()

        self.consume("COLON")
        self.consume("NEWLINE")
        self.consume("INDENT")

        body = []
        while self.current is not None and self.peek_kind() != "DEDENT":
            kind = self.parse_kind(self.peek_kind())
            if kind is not None:
                body.append(kind)
            else:
                self.advance()

        end_token = self.current
        self.consume("DEDENT")
        line = self._block_line(start_token, end_token)

        return ForAST(target, source, body, line=line, node_id=self.id_alloc.alloc())

    def accepts_decorators(self, func):
        sig = inspect.signature(func)
        return "decorators" in sig.parameters or any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
        )

    def parse_import(self):
        start_token = self.current
        self.consume("IMPORT")
        module_token = self.consume("NAME")
        module_name = module_token[1]

        alias = None
        end_token = module_token
        if self.peek_kind() == "AS":
            self.advance()
            alias_token = self.consume("NAME")
            alias = alias_token[1]
            end_token = alias_token

        line = self._make_line(start_token, end_token)
        return ImportAST(
            module=module_name,
            symbols=[],
            alias=alias,
            line=line,
            node_id=self.id_alloc.alloc(),
        )

    def parse_from(self):
        start_token = self.current
        self.consume("FROM")
        module_token = self.consume("NAME")
        module_name = module_token[1]

        self.consume("IMPORT")

        symbols = []
        end_token = module_token
        while self.current is not None and self.peek_kind() != "NEWLINE":
            sym_token = self.consume("NAME")
            alias_token = None
            if self.peek_kind() == "AS":
                self.advance()
                alias_token = self.consume("NAME")

            end_token = alias_token or sym_token

            symbols.append(
                {
                    "name": sym_token[1],
                    "alias": alias_token[1] if alias_token is not None else None,
                }
            )
            if self.peek_kind() == "COMMA":
                self.advance()
            else:
                break

        line = self._make_line(start_token, end_token)
        return ImportAST(
            module=module_name,
            symbols=symbols,
            alias=None,
            line=line,
            node_id=self.id_alloc.alloc(),
        )

    def parse_kind(self, kind):
        if kind is None:
            return None

        if kind in ("DEDENT", "RPAREN", "COMMA", "ELIF", "ELSE"):
            self.print_error(f"Syntax Error: Unexpected '{kind}'")

        func = self.keywords.get(kind)
        if func is not None:
            accept_decorators = self.accepts_decorators(func)
            if accept_decorators:
                return func(decorators=self.last_decorators)
            elif not accept_decorators and self.last_decorators:
                self.print_error("Syntax Error: Unexpected decorator")
            else:
                return func()

        if kind == "AT":
            decorators = self.parse_decorator()
            if decorators:
                self.last_decorators.append(decorators)
            return None

        if kind == "NEWLINE":
            return None

        if self.last_decorators:
            self.print_error("Syntax Error: Unexpected decorator")

        if kind == "RETURN":
            return self.parse_return()

        if kind == "NAME":
            return self.parse_name()

        if kind == "NUMBER":
            return self.parse_number()

        if kind == "IMPORT":
            return self.parse_import()

        if kind == "FROM":
            return self.parse_from()

        if kind == "STRING":
            token = self.advance()
            line = self._make_line(token)
            return StringAST(value=token[1], line=line, node_id=self.id_alloc.alloc())

        if kind == "PASS":
            token = self.advance()
            line = self._make_line(token)
            return PassAST(line=line, node_id=self.id_alloc.alloc())

        if kind == "LPAREN":
            start_token = self.current
            self.advance()
            expr = self.parse_kind(self.peek_kind())
            end_token = self.current
            self.consume("RPAREN")
            return expr

        if kind in ("PLUS", "MINUS", "STAR", "SLASH", "EQEQ", "NEQ", "GT", "LT"):
            token = self.advance()
            line = self._make_line(token)
            return OperatorAST(op=token[1], line=line, node_id=self.id_alloc.alloc())

        return None

    def parse_all(self):
        while self.current is not None:
            kind = self.peek_kind()
            res = self.parse_kind(kind)
            if res is not None:
                self.asts.append(res)
            else:
                self.advance()

    def run(self):
        self.parse_all()
        return self.asts
