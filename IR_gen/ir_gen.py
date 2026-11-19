from .irs import *
from nida_ast.base import *
from type_systems.types import ClassType, Type, resolve_type
from utils.errors import *
from semantic.tree_systems.symbol_types import *


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

        return IfIR(
            cond=cond,
            body=body,
            elifs=elifs,
            else_body=else_body_irs,
            if_sym=lk,
            node_id=self.get_id(ast),
        )

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

        ir = IntrinsicCallIR(
            intrinsic=intrinsic,
            target=target,
            args=args,
            type=type,
            node_id=self.get_id(ast),
        )

        # handler = intrinsic.handler
        # new_ir = handler(ir)
        return ir

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
        return StringLiteralIR(value=ast.value, node_id=self.get_id(ast))

    def gen_BooleanAST(self, ast):
        value = ast.value
        return BooleanIR(value=value, node_id=self.get_id(ast))

    def gen_NoneAST(self, ast):
        return NoneIR(node_id=self.get_id(ast))

    def gen_UnaryOpAST(self, ast):
        op = ast.op

        lk = self.get_lk(ast)
        type = lk.type
        # raise Exception(ast)
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

    # def gen_AssignAST(self, ast):
    #     value = ast.value
    #     var_type = ast.type
    #     is_re_assign = False

    #     lk = self.get_lk(ast)

    #     target = lk.name

    #     var_type = lk.type

    #     is_re_assign = lk.parent_assign is not None

    #     field = ast.field
    #     field_ir = self.gen(field) if field is not None else None

    #     # if isinstance(value, UnaryOpAST):
    #     #     val_res = self._gen_unary_op(target, value)
    #     if value is None:
    #         val_res = NoneIR(air=True, node_id=self.get_id(ast))
    #     else:
    #         val_res = self.gen(value)

    #     if hasattr(val_res, "type") and val_res.type is None:
    #         val_res.type = var_type

    #     return AssignIR(
    #         name=target,
    #         value=val_res,
    #         type=var_type,
    #         re_assign=is_re_assign,
    #         field=field_ir,
    #         node_id=self.get_id(ast),
    #     )

    # def _type_of(self, type_val):
    #     """A type written as a name ('int', 'Point') becomes a type object."""
    #     if type_val is None or isinstance(type_val, Type):
    #         return type_val

    #     resolved = resolve_type(type_val)

    #     if resolved is not None:
    #         return resolved

    #     return type_val

    # def _get_name_from_IdentifierAST(self, ast):
    #     lk = self.get_lk(ast)
    #     field_name = lk.resolve_name
    #     return field_name

    # def gen_FieldAccessAST(self, ast):
    #     lk = self.get_lk(ast)
    #     target_ir = self.gen(ast.target)
    #     field = ast.field

    #     idn_lk = self.get_lk(ast.field)
    #     idn_name = self._get_name_from_IdentifierAST(field)

    #     field_ir = FieldAccessIR(
    #         target=target_ir,
    #         field=idn_name,
    #         type=self._type_of(lk.type),
    #         node_id=self.get_id(ast),
    #     )

    #     # raise Exception(idn_lk)
    #     return field_ir

    # def gen_SelfAST(self, ast):
    #     lk = self.get_lk(ast)
    #     type = ClassType(lk.class_name)
    #     return VariableIR(name="self", type=type, node_id=self.get_id(ast))

    # def gen_ReturnAST(self, ast):
    #     value = ast.value
    #     res = self.gen(value)
    #     return ReturnIR(value=res, node_id=self.get_id(ast))

    # def gen_symbol_ref(self, sym):
    #     if isinstance(sym, VariableSymbol):
    #         if sym.name == "self":
    #             lookup = sym.lookup
    #             class_name = lookup.name
    #             # raise Exception(class_name)
    #             class_ref_type = ClassType(class_name)
    #             return VariableIR(name=sym.name, type=class_ref_type)

    #         return self.gen_symbol_ref(sym.lookup)

    #     if isinstance(sym, AssignSymbol):
    #         return VariableIR(
    #             name=sym.name, type=sym.type, node_id=self.get_id(sym.ast_node)
    #         )

    #     if isinstance(sym, FieldAccessSymbol):
    #         target = self.gen_symbol_ref(sym.target)
    #         field = sym.field

    #         return FieldAccessIR(
    #             target=target,
    #             field=field.lookup.name,
    #             type=sym.type,
    #             node_id=self.get_id(sym.ast_node),
    #         )

    #     raise NidavellirInternalError(f"Cannot generate symbol reference: {sym!r}")

    # def gen_CallAST(self, ast):
    #     lk = self.get_lk(ast)
    #     if isinstance(lk, IntrinsicCallSymbol):
    #         return self.gen_IntrinsicCallAST(ast)

    #     target = lk.lookup.name
    #     field = ast.field
    #     field_ir = self.gen(field) if field is not None else None
    #     args = ast.args
    #     type = lk.type

    #     args_irs = []
    #     for arg in args:
    #         args_irs.append(self.gen(arg))

    #     ref_type = lk.class_ref_type

    #     if ref_type is not None:
    #         self_ir = self.gen(ref_type.instance_lk.ast_node)
    #         args_irs.insert(0, self_ir)

    #     ir = CallIR(
    #         name=target,
    #         args=args_irs,
    #         type=type,
    #         field=field_ir,
    #         node_id=self.get_id(ast),
    #     )
    #     return ir

    # def gen_IntrinsicCallAST(self, ast):
    #     lk = self.get_lk(ast)
    #     intrinsic = lk.intrinsic
    #     name = intrinsic.name
    #     args = ast.args
    #     type = lk.type

    #     n_args = []
    #     for arg in args:
    #         n_args.append(self.gen(arg))

    #     ir = IntrinsicCallIR(
    #         intrinsic=intrinsic,
    #         name=name,
    #         args=n_args,
    #         type=type,
    #         node_id=self.get_id(ast),
    #     )
    #     handler = intrinsic.handler
    #     new_ir = handler(ir)
    #     return new_ir

    # def gen_StringAST(self, ast):
    #     return StringLiteralIR(value=ast.value, node_id=self.get_id(ast))

    # def gen_NumberAST(self, ast):
    #     id = ast.node_id
    #     if id is None:
    #         raise NidavellirInternalError("No node_id for NumberAST")

    #     lk = self.stm.lookup_symbol_id(id)
    #     if lk is None:
    #         raise NidavellirNameError(f"Symbol '{id}' is not defined", ast.line)

    #     type = lk.type

    #     return NumberIR(value=ast.value, type=type, node_id=self.get_id(ast))

    # def gen_VariableAST(self, ast):
    #     lk = self.get_lk(ast)
    #     name = lk.name
    #     type = lk.type
    #     if type is None:
    #         if (
    #             hasattr(lk, "lookup")
    #             and lk.lookup is not None
    #             and lk.lookup.type is not None
    #         ):
    #             type = lk.lookup.type
    #         else:
    #             raise Exception(lk)
    #             raise NidavellirInternalError(f"No type for VariableAST")

    #     return VariableIR(name=name, type=type, node_id=self.get_id(ast))

    # def gen_BinaryOpAST(self, ast):
    #     left = ast.left
    #     left_ir = self.gen(left)
    #     right = ast.right
    #     right_ir = self.gen(right)
    #     op = ast.op

    #     lk = self.get_lk(ast)
    #     type = lk.type

    #     return BinaryOpIR(
    #         left=left_ir, right=right_ir, op=op, type=type, node_id=self.get_id(ast)
    #     )

    # def gen_FunctionAST(self, ast):
    #     lk = self.get_lk(ast)

    #     name = lk.name
    #     type = lk.type

    #     is_called = lk.is_called
    #     if not is_called:
    #         return None

    #     decs = ast.decorators
    #     args = ast.args
    #     body = ast.body

    #     args_irs = []
    #     for arg in args:
    #         args_irs.append(self.gen(arg))

    #     ir_body = []

    #     for b in body:
    #         res = self.gen(b)
    #         ir_body.append(res)

    #     ir = FunctionIR(
    #         name=name,
    #         args=args_irs,
    #         body=ir_body,
    #         ast_name=ast.name,
    #         type=type,
    #         node_id=self.get_id(ast),
    #     )

    #     return ir

    # def gen_ImportAST(self, ast):
    #     module_name = ast.module
    #     symbols = ast.symbols
    #     alias = ast.alias

    #     body = []
    #     module = ast.resolved_module

    #     for n in module.asts:
    #         body.append(self.gen(n))

    #     module.hirs = body

    #     return IRImport(
    #         module=module_name,
    #         symbols=symbols,
    #         alias=alias,
    #         resolved_module=module,
    #         node_id=self.get_id(ast),
    #     )

    # def gen_BlockAST(self, ast):
    #     body = ast.body
    #     body_irs = []
    #     for n in body:
    #         body_irs.append(self.gen(n))

    #     return BlockIR(body=body_irs, node_id=self.get_id(ast))

    # def gen_ElifAST(self, ast):
    #     cond = ast.cond
    #     body = ast.body

    #     cond_ir = self.gen(cond)
    #     body_irs = []
    #     for n in body:
    #         body_irs.append(self.gen(n))

    #     return ElifIR(cond=cond_ir, body=body_irs, node_id=self.get_id(ast))

    # def gen_IfAST(self, ast):
    #     cond = ast.cond
    #     body = ast.body
    #     elifs = ast.elifs
    #     else_body = ast.else_body
    #     lk = self.get_lk(ast)

    #     cond_ir = self.gen(cond)
    #     body_irs = []
    #     for n in body:
    #         body_irs.append(self.gen(n))

    #     elifs_irs = []
    #     for elif_ast in elifs:
    #         elif_ir = self.gen(elif_ast)
    #         elifs_irs.append(elif_ir)

    #     else_body_irs = self.gen(else_body) if else_body is not None else None

    #     return IfIR(
    #         cond=cond_ir,
    #         body=body_irs,
    #         elifs=elifs_irs,
    #         else_body=else_body_irs,
    #         if_sym=lk,
    #         node_id=self.get_id(ast),
    #     )

    # # TODO: impl
    # # def gen_GroupAST(self, ast):
    # #     expr = ast.expr
    # #     expr_ir = self.gen(expr)
    # #     return GroupIR(expr_ir)

    # def gen_ForAST(self, ast):
    #     target = ast.target
    #     source = ast.source
    #     body = ast.body

    #     target_ir = self.gen(target)
    #     source_ir = self.gen(source)
    #     body_irs = []
    #     for n in body:
    #         body_irs.append(self.gen(n))

    #     return ForIR(
    #         target=target_ir, source=source_ir, body=body_irs, node_id=self.get_id(ast)
    #     )

    # # TODO: impl
    # # def gen_WhileAST(self, ast):
    # #     cond = ast.cond
    # #     body = ast.body

    # #     body_irs = []
    # #     for n in body:
    # #         body_irs.append(self.gen(n))

    # #     cond_ir = self.gen(cond)
    # #     return WhileIR(cond_ir, body_irs)

    # def gen_BooleanAST(self, ast):
    #     value = ast.value
    #     return BooleanIR(value=value, node_id=self.get_id(ast))

    # def gen_NoneAST(self, ast):
    #     return NoneIR(node_id=self.get_id(ast))

    # def gen_DefinitionAST(self, ast):
    #     lk = self.get_lk(ast)
    #     target = lk.name
    #     type = lk.type

    #     value = ast.value

    #     value_ir = self.gen(value)
    #     return DefinitionIR(
    #         name=target, value=value_ir, type=type, node_id=self.get_id(ast)
    #     )

    # def gen_UnaryOpAST(self, ast):
    #     op = ast.op
    #     value = ast.right

    #     lk = self.get_lk(ast)
    #     type = lk.type

    #     value_ir = self.gen(value)
    #     return UnaryOpIR(op=op, value=value_ir, type=type, node_id=self.get_id(ast))

    # # TODO: impl
    # # def gen_ListLiteralAST(self, ast):
    # #     elements = []

    # #     for e in ast.elements:
    # #         element_ir = self.gen(e)
    # #         elements.append(element_ir)

    # #     lk = self.get_lk(ast)
    # #     type = lk.type

    # #     literal_ir = ListLiteralIR(elements, type)
    # #     literal_ir.element_list_id = self._next_list_id()
    # #     return literal_ir

    # def _next_list_id(self):
    #     list_id = self.list_literal_count
    #     self.list_literal_count += 1
    #     return list_id

    # def process_class_body(self, body):
    #     new_body = []

    #     for n in body:
    #         if isinstance(n, AssignAST):
    #             res = self.gen(n)
    #             if res is None:
    #                 raise Exception(f"No IR generated for {n}")

    #             new_body.append(res)

    #         elif isinstance(n, FunctionAST):
    #             res = self.gen(n)
    #             if res is None:
    #                 continue
    #                 raise Exception(f"No IR generated for {n}")

    #             new_body.append(res)

    #         else:
    #             raise Exception(f"No IR generated for {n}")

    #     return new_body

    # def _class_fields(self, ast):
    #     lk = self.get_lk(ast)
    #     fields = []
    #     raw_fields = lk.fields
    #     for key, val in raw_fields.items():
    #         name = val.name
    #         type = val.type
    #         default_value = val.value
    #         fields.append((name, type, default_value))

    #     # raise Exception(fields)
    #     return fields

    # def gen_ClassAST(self, ast):
    #     id = ast.node_id
    #     name = ast.name
    #     body = ast.body

    #     new_body = self.process_class_body(body)

    #     return ClassIR(
    #         name=name,
    #         body=new_body,
    #         fields=self._class_fields(ast),
    #         node_id=self.get_id(ast),
    #     )

    # def _gen_unary_op(self, target, ast):
    #     op = ast.op
    #     right = ast.right

    #     right_ir = self.gen(right)
    #     return BinaryOpIR(
    #         left=VariableIR(target), op=op, right=right_ir, node_id=self.get_id(ast)
    #     )

    # def gen(self, ast):
    #     name = ast.__class__.__name__
    #     if name == "NoneType":
    #         raise Exception(f"No function named {ast}")

    #     func = getattr(self, f"gen_{name}")
    #     if func is None:
    #         raise Exception(f"No function named {name}")

    #     res = func(ast)
    #     return res

    # def gen_from_list(self, asts):
    #     for ast in asts:
    #         res = self.gen(ast)
    #         if res is not None:
    #             self.IRs.append(res)

    #     # raise Exception(self.IRs)

    #     ir_passer = IRPasser(self.IRs, self.ctx)
    #     self.IRs = ir_passer.run()

    #     return self.IRs
