from .irs import *
from .ir_destinations import *
from type_systems.types import *
from utils.errors import *


class IR_Box:
    __slots__ = ("ir", "destination")

    def __init__(self, ir, destination=Main):
        self.ir = ir if isinstance(ir, list) else [ir]
        self.destination = destination

    def __repr__(self):
        return f"IR_Box(destination={self.destination.__name__}, " f"ir={self.ir!r})"


class IRPasser:
    def __init__(self, irs, ctx):
        self.id_alloc = ctx["id_alloc"]
        self.irs = irs
        self.ctx = ctx
        self.generated_functions = {}

    def run(self):
        final_irs = []
        main_stmts = []
        pre_main_stmts = []
        if not self.irs:
            raise NidavellirSyntaxError(
                "No executable code found. The file is empty or contains no reachable functions."
            )

        for ir in self.irs:
            for result in self.run_stmt(ir):
                if result.destination is Module:
                    final_irs.extend(result.ir)
                elif result.destination is Main:
                    main_stmts.extend(result.ir)
                elif result.destination is PreMain:
                    pre_main_stmts.extend(result.ir)
                else:
                    raise ValueError(
                        f"Unknown IR destination: " f"{result.destination!r}"
                    )

        num = NumberIR("0")
        num.type = IntType(byte_size=4, signed=True)

        main_stmts.append(ReturnIR(num, type=num.type))

        main_fn = FunctionIR(
            decs=[],
            name="main",
            args=[],
            body=[*pre_main_stmts, *main_stmts],
            type=IntType(byte_size=4, signed=True),
            is_main_func=True,
        )

        final_irs.append(main_fn)
        return final_irs

    def run_stmt(self, ir):
        name = type(ir).__name__
        func = getattr(self, f"stmt_{name}", self.default_stmt_pass)
        result = func(ir)

        if not isinstance(result, list) or not all(
            isinstance(item, IR_Box) for item in result
        ):
            raise TypeError(
                f"{func.__name__} must return list[IR_Box], "
                f"got {type(result).__name__}"
            )

        return result

    def run_stmts(self, stmts):
        new_stmts = []

        for stmt in stmts:
            for result in self.run_stmt(stmt):
                new_stmts.extend(result.ir)

        return new_stmts

    def run_expr(self, ir):
        name = type(ir).__name__
        func = getattr(self, f"expr_{name}", self.default_expr_pass)
        return func(ir)

    def default_stmt_pass(self, ir):
        return [IR_Box(ir)]

    def default_expr_pass(self, ir):
        return ir

    def process_CallIR(self, ir, is_expr=False):
        if ir.field is not None:
            field = ir.field

            if not isinstance(field, FieldAccessIR):
                raise NidavellirInternalError(
                    f"Expected FieldAccessIR, got {type(field).__name__}",
                    ir.line,
                )

            receiver = self.run_expr(field.target)

            ir.target = field.field
            ir.args = [
                receiver,
                *(self.run_expr(arg) for arg in ir.args),
            ]
            ir.field = None

        else:
            ir.args = [self.run_expr(arg) for arg in ir.args]

            if ir.target in self.generated_functions:
                ir.target = self.generated_functions[ir.target].name

        if is_expr:
            return ir

        return [IR_Box(ir)]

    def stmt_CallIR(self, ir):
        return self.process_CallIR(ir)

    def expr_CallIR(self, ir):
        return self.process_CallIR(ir, is_expr=True)

    def stmt_AssignIR(self, ir):
        ir.value = self.run_expr(ir.value)
        return [IR_Box(ir)]

    def stmt_DefinitionIR(self, ir):
        value = self.run_expr(ir.value)

        asgn = AssignIR(ir.target, value, ir.type)
        asgn.re_assign = True

        fn_name = self.f_alloc.anon()

        fn = FunctionIR(
            decs=None,
            name=fn_name,
            args=[],
            body=[asgn],
            type=NoneType(),
            is_main_func=False,
            is_static=True,
        )

        fn_call = CallIR(fn_name, [])
        ir.initializer = fn_name

        return [
            IR_Box(ir, destination=Module),
            IR_Box(fn, destination=Module),
            IR_Box(fn_call, destination=PreMain),
        ]

    def stmt_ReturnIR(self, ir):
        if ir.value is not None:
            ir.value = self.run_expr(ir.value)

        return [IR_Box(ir)]

    def stmt_FunctionIR(self, ir):
        new_body = self.run_stmts(ir.body)

        ir.body = new_body
        return [IR_Box(ir, destination=Module)]

    def stmt_WhileIR(self, ir):
        new_body = self.run_stmts(ir.body)

        ir.body = new_body

        if ir.cond is not None:
            ir.cond = self.run_expr(ir.cond)

        return [IR_Box(ir)]

    def stmt_ClassIR(self, ir):
        cl_body = self.run_stmts(ir.body)
        class_name = ir.name

        assignments = []
        functions = []

        for b in cl_body:
            if isinstance(b, AssignIR):
                assignments.append(b)
            elif isinstance(b, FunctionIR):
                functions.append(b)
            else:
                raise Exception(f"No IR generated for {b}")

        fields = []
        for field in assignments:
            fields.append((field.target, field.type, field.value))

        struct = StructIR(ir.name, assignments, fields)
        # raise Exception(struct)

        methods = [fn for fn in functions if fn.ast_name != "__init__"]

        init_func = self._class_initializer(ir, functions)

        struct.initialize_function = init_func
        self.generated_functions[class_name] = init_func

        return [
            IR_Box(struct, destination=Module),
            IR_Box(methods, destination=Module),
        ]

    def _class_initializer(self, ir, functions):
        init = None

        for fn in functions:
            if fn.ast_name == "__init__":
                init = fn
                break

        class_type = ClassType(ir.name)
        fn_name = self.id_alloc.anon()

        # TODO: add field setters support
        # field_setters = []

        body = [
            AssignIR(
                "self",
                NewIR(ir.name, class_type),
                class_type,
            ),
            # *field_setters,
        ]

        if init is not None:
            body.extend(init.body)

        body.append(ReturnIR(VariableIR("self", class_type), type=class_type))

        args = init.args[1:] if init is not None else []

        return FunctionIR(
            decs=[],
            name=fn_name,
            args=args,
            body=body,
            type=class_type,
            is_main_func=False,
            is_static=False,
        )

    def _field_setter(self, class_type, field_name, field_type, default_value):
        if default_value is None:
            if not isinstance(field_type, ClassType):
                return None

            default_value = self.run_expr(CallIR(field_type.name, [], field_type))

        return AssignIR(
            "self",
            default_value,
            field_type,
            chain=[field_name],
            base_type=class_type,
            chain_types=[field_type],
        )

    def stmt_IfIR(self, ir):
        if_sym = ir.if_sym
        merges = if_sym.merges
        assigns = []

        for merge in merges:
            assign_sym = merge.merge_sym

            if assign_sym.parent_assign is not None:
                continue

            assign_ir = AssignIR(
                assign_sym.name,
                NoneIR(True),
                assign_sym.type,
            )

            assigns.append(IR_Box(assign_ir, destination=PreMain))

        return [*assigns, IR_Box(ir)]

    def stmt_IRImport(self, ir):
        body = ir.resolved_module.hirs
        new_body = self.run_stmts(body)

        ir.resolved_module.hirs = new_body

        return [IR_Box(ir)]

    def expr_BinaryOpIR(self, ir):
        ir.left = self.run_expr(ir.left)
        ir.right = self.run_expr(ir.right)
        return ir
