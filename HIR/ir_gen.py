from .irs import *
from AST.base import *
from type_systems.types import ClassType, Type, resolve_type
from utils.errors import *
from semantic.symbol_types import *


class IRGen:
    def __init__(self, asts, ctx):
        self.asts = asts
        self.ctx = ctx
        self.id_alloc = ctx["id_alloc"]
        self.stm = ctx["stm"]

        self.IRs = []

    # ---------------------
    # ------ Heplers ------
    # ---------------------

    def get_id(self, node):
        id = node.node_id
        if id is None:
            raise NidavellirInternalError(f"No node_id for {type(node).__name__}")

        return id

    def get_lk(self, node):
        id = self.get_id(node)

        lk = self.stm.lookup_symbol_id(id)

        if lk is None:
            raise NidavellirNameError(f"Symbol '{id}' is not defined", node.line)

        return lk

    def _create_function_arg(self, name, type, default, id):
        return ParameterIR(name=name, type=type, default=default, node_id=id)

    def _create_self_arg(self, ast):
        lk = self.get_lk(ast)
        if lk.type is None:
            raise NidavellirInternalError("SelfAST has no resolved class type")

        return ParameterIR(
            name="self",
            type=lk.type,
            default=NoneIR(),
            node_id=self.get_id(ast),
        )

    def _gen_func_args(self, args):
        new_args = []

        for arg in args:
            if isinstance(arg, SelfAST):
                new_args.append(self._create_self_arg(arg))
                continue

            if not isinstance(arg, AssignAST):
                raise NidavellirInternalError(
                    f"Function args must be AssignAST or SelfAST, got {type(arg).__name__}"
                )

            lk = self.get_lk(arg)
            value = self.gen_expr(arg.value) if arg.value is not None else NoneIR()

            new_args.append(
                self._create_function_arg(
                    lk.name,
                    lk.type,
                    value,
                    self.get_id(arg),
                )
            )

        return new_args

    def _gen_call_args(self, args: list[AST]) -> list[ExprIR]:
        return [self.gen_expr(arg) for arg in args]

    def _create_class_fields(self, lk):
        fields = []
        for key, val in lk.fields.items():
            default_ast = getattr(val.ast_node, "value", None)

            decl = FieldDeclIR(
                name=val.name,
                default=self.gen_expr(default_ast) if default_ast is not None else None,
                type=val.type,
                node_id=self.get_id(val),
            )
            fields.append(decl)

        return fields

    def _get_name_from_IdentifierAST(self, ast):
        lk = self.get_lk(ast)
        return lk.resolve_name

    def _translate_sym_to_ir(self, sym: AssignSymbol | MergeAssignmentSymbol):
        if isinstance(sym, MergeAssignmentSymbol) and sym.merge_sym is not None:
            return self._translate_sym_to_ir(sym.merge_sym)
        else:
            return AssignIR(
                target=IdentifierIR(name=sym.name),
                value=NoneIR(air=True),
                type=sym.type,
            )

    def _create_if_merges(self, merge_syms):
        merges = []
        for merge in merge_syms:
            if merge.merge_sym.parent_assign is not None:
                continue

            merges.append(self._translate_sym_to_ir(merge))
        # return [self._translate_sym_to_ir(sym) for sym in merge_syms]
        return merges

    # ---------------------
    # ----- Statement -----
    # ---------------------

    def gen_AssignAST(self, ast):
        lk = self.get_lk(ast)

        re_assign = lk.parent_assign is not None

        target = (
            self.gen_expr(ast.field)
            if ast.field is not None
            else IdentifierIR(name=lk.name)
        )

        value = (
            self.gen_expr(ast.value)
            if ast.value is not None
            else NoneIR(air=True, node_id=self.get_id(ast))
        )

        return AssignIR(
            target=target,
            value=value,
            type=lk.type,
            re_assign=re_assign,
            node_id=self.get_id(ast),
        )

    def gen_PassAST(self, ast):
        return PassIR(node_id=self.get_id(ast))

    def gen_FunctionAST(self, ast):
        lk = self.get_lk(ast)

        name = lk.name
        type = lk.type

        is_called = lk.is_called
        if not is_called:
            return EliminatedIR()

        args = self._gen_func_args(ast.args)

        body = self.gen_stmts(ast.body)

        return FunctionIR(
            name=name,
            args=args,
            body=body,
            ast_name=ast.name,
            type=type,
            node_id=self.get_id(ast),
        )

    def gen_ReturnAST(self, ast):
        value = self.gen_expr(ast.value) if ast.value is not None else NoneIR(air=True)
        return ReturnIR(value=value, node_id=self.get_id(ast))

    def gen_BlockAST(self, ast):
        body = self.gen_stmts(ast.body)

        return BlockIR(body=body, node_id=self.get_id(ast))

    def gen_ElifAST(self, ast):
        cond = self.gen_expr(ast.cond)
        body = self.gen_stmts(ast.body)

        return ElifIR(cond=cond, body=body, node_id=self.get_id(ast))

    def gen_IfAST(self, ast):
        lk = self.get_lk(ast)

        cond = self.gen_expr(ast.cond)
        body = self.gen_stmts(ast.body)
        elifs = self.gen_stmts(ast.elifs)

        else_body_irs = (
            self.gen_stmt(ast.else_body) if ast.else_body is not None else None
        )
        If = IfIR(
            cond=cond,
            body=body,
            elifs=elifs,
            else_body=else_body_irs,
            if_sym=lk,
            node_id=self.get_id(ast),
        )
        merges = self._create_if_merges(lk.merges)
        body = [*merges, If]
        return BlockIR(body=body, node_id=self.get_id(ast))

    def gen_ClassAST(self, ast):
        name = ast.name
        lk = self.get_lk(ast)

        fields = self._create_class_fields(lk)
        field_ids = {field.node_id for field in fields}

        body = [
            self.gen_stmt(stmt)
            for stmt in ast.body
            if self.get_id(stmt) not in field_ids
        ]

        return ClassIR(
            name=name,
            body=body,
            fields=fields,
            node_id=self.get_id(ast),
        )

    def gen_WhileAST(self, ast):
        cond = self.gen_expr(ast.cond)
        body = self.gen_stmts(ast.body)

        return WhileIR(cond=cond, body=body, node_id=self.get_id(ast))

    def gen_BreakAST(self, ast):
        return BreakIR(node_id=self.get_id(ast))

    def gen_ContinueAST(self, ast):
        return ContinueIR(node_id=self.get_id(ast))

    # ---------------------
    # ---- Expression -----
    # ---------------------

    def gen_SelfAST(self, ast):
        lk = self.get_lk(ast)
        return VariableIR(
            name="self",
            type=ClassType(lk.class_name),
            node_id=self.get_id(ast),
        )

    def gen_BinaryOpAST(self, ast):
        left = self.gen_expr(ast.left)
        right = self.gen_expr(ast.right)
        op = ast.op

        lk = self.get_lk(ast)
        type = lk.type

        return BinaryOpIR(
            left=left, right=right, op=op, type=type, node_id=self.get_id(ast)
        )

    def gen_NumberAST(self, ast):
        lk = self.get_lk(ast)

        type = lk.type

        return NumberIR(value=ast.value, type=type, node_id=self.get_id(ast))

    def gen_VariableAST(self, ast):
        lk = self.get_lk(ast)
        name = lk.name
        type = lk.type

        return VariableIR(name=name, type=type, node_id=self.get_id(ast))

    def gen_IntrinsicCallAST(self, ast):
        lk = self.get_lk(ast)

        type = lk.type
        intrinsic = lk.intrinsic

        name = intrinsic.name
        target = IdentifierIR(name=name)

        args = self._gen_call_args(ast.args)

        return IntrinsicCallIR(
            intrinsic=intrinsic,
            target=target,
            args=args,
            type=type,
            node_id=self.get_id(ast),
        )

    def gen_CallAST(self, ast):
        lk = self.get_lk(ast)
        if isinstance(lk, IntrinsicCallSymbol):
            return self.gen_IntrinsicCallAST(ast)

        name = lk.lookup.name
        field = self.gen_expr(ast.field) if ast.field is not None else None
        if field is not None:
            target = field
        else:
            target = IdentifierIR(name=name)

        type = lk.type

        args = self._gen_call_args(ast.args)

        return CallIR(
            target=target,
            args=args,
            type=type,
            node_id=self.get_id(ast),
        )

    def gen_StringAST(self, ast):
        return StringLiteralIR(
            value=ast.value, node_id=self.get_id(ast), type=StringType()
        )

    def gen_BooleanAST(self, ast):
        value = ast.value
        return BooleanIR(value=value, node_id=self.get_id(ast))

    def gen_NoneAST(self, ast):
        return NoneIR(node_id=self.get_id(ast))

    def gen_UnaryOpAST(self, ast):
        op = ast.op

        lk = self.get_lk(ast)
        type = lk.type

        value = self.gen_expr(ast.right)
        return UnaryOpIR(op=op, value=value, type=type, node_id=self.get_id(ast))

    def gen_FieldAccessAST(self, ast):
        lk = self.get_lk(ast)
        target_ir = self.gen(ast.target)
        field = ast.field

        idn_name = self._get_name_from_IdentifierAST(field)

        field_ir = FieldAccessIR(
            target=target_ir,
            field=idn_name,
            type=lk.type,
            node_id=self.get_id(ast),
        )

        # raise Exception(idn_lk)
        return field_ir

    def gen_IndexAccessAST(self, ast):
        target = self.gen_expr(ast.target)
        index = self.gen_expr(ast.index)

        return IndexAccessIR(target=target, index=index, node_id=self.get_id(ast))

    # ---------------------
    # ---- Generators -----
    # ---------------------

    def gen(self, ast):
        if ast is None:
            return None

        name = type(ast).__name__
        func = getattr(self, f"gen_{name}", None)

        if func is None:
            raise NidavellirInternalError(f"No HIR generator for {name}")

        return func(ast)

    def gen_expr(self, ast):
        result = self.gen(ast)

        if not isinstance(result, ExprIR):
            raise NidavellirInternalError(
                f"Expected ExprIR from {type(ast).__name__}, "
                f"got {type(result).__name__}"
            )

        return result

    def gen_stmt(self, ast):
        result = self.gen(ast)

        if isinstance(result, ExprIR):
            return StmtExprIR(
                expr=result,
                node_id=self.get_id(ast),
            )

        if not isinstance(result, StmtIR):
            raise NidavellirInternalError(
                f"Expected StmtIR from {type(ast).__name__}, "
                f"got {type(result).__name__}"
            )

        return result

    def gen_stmts(self, asts):
        return [self.gen_stmt(ast) for ast in asts]

    def run(self):
        return self.gen_stmts(self.asts)
