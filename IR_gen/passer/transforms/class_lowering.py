from ..transformer import IRTransform, PassContractError, ReplaceMany
from ...irs import *
from ...ir_gen import IRGen
from semantic.tree_systems.symbol_types import (
    AssignSymbol,
    IdentifierSymbol,
    VariableSymbol,
)
from type_systems.types import BoundMethodType


class ClassLowering(IRTransform):
    def __init__(self):
        self.generated_functions = {}
        self.generator = None

    def visit(self, ir):
        if isinstance(ir, ClassIR):
            return ReplaceMany(self.class_lower(ir))
        if isinstance(ir, CallIR):  # and isinstance(ir.target, IdentifierIR):
            return self.process_call(ir)
        if isinstance(ir, AssignIR) and isinstance(ir.type, BoundMethodType):
            return self.process_assign_field(ir)
        if (
            isinstance(ir, ReturnIR)
            and isinstance(ir.value, FieldAccessIR)
            and isinstance(ir.value.type, ClassMethodRefType)
        ):
            self.changed = True
            ir.value = BoundMethodIR(
                receiver=ir.value.target,
                method=ir.value.type.lk.name,
                type=ir.value.type,
                node_id=ir.value.node_id,
            )
            return ir
        return ir

    def generate_self_ref(self, instance_lk):
        if self.generator is None:
            self.generator = IRGen([], self.ctx)

        self_ref_ir = self.generator.gen(instance_lk.ast_node)
        return self_ref_ir

    def get_lk(self, ir):
        node_id = ir.node_id
        if node_id is None:
            return

        lk = self.ctx["stm"].lookup_symbol_id(node_id)

        return lk

    def process_assign_field(self, ir):
        value = ir.value

        if isinstance(value, FieldAccessIR) and isinstance(
            value.type, ClassMethodRefType
        ):
            self.changed = True
            ir.value = BoundMethodIR(
                receiver=value.target,
                method=value.type.lk.name,
                type=ir.type,
                node_id=value.node_id,
            )

        return ir

    def process_call(self, ir):
        if isinstance(ir.target, IdentifierIR):
            bound = self._bound_type(self.get_lk(ir))
            if bound is not None:
                self.changed = True
                return BoundCallIR(
                    bound=VariableIR(
                        name=ir.target.name,
                        type=bound,
                        node_id=ir.target.node_id,
                    ),
                    args=ir.args,
                    type=ir.type,
                    ref=bound.ref,
                    node_id=ir.node_id,
                )

            generated = self.generated_functions.get(ir.target.name)
            if generated is not None:
                ir.target = IdentifierIR(
                    name=generated.name,
                    type=ir.target.type,
                    node_id=ir.target.node_id,
                )
                self.changed = True

        lk = self.get_lk(ir)
        class_ref = lk.class_ref_type if lk is not None else None
        if class_ref is not None:
            instance_lk = class_ref.instance_lk
            self_ref_ir = self.generate_self_ref(instance_lk)
            ir.args.insert(0, self_ref_ir)

        return ir

    def _bound_type(self, lk):
        if lk is None:
            return None

        current = getattr(lk, "lookup", None)
        seen = set()

        while current is not None and id(current) not in seen:
            seen.add(id(current))

            if isinstance(current, (AssignSymbol, IdentifierSymbol, VariableSymbol)):
                type = getattr(current, "type", None)
                if isinstance(type, BoundMethodType):
                    return type

            current = getattr(current, "value", None) or getattr(
                current, "lookup", None
            )

        return None

    def class_lower(self, ir):
        functions = [stmt for stmt in ir.body if isinstance(stmt, FunctionIR)]

        for stmt in ir.body:
            if not isinstance(stmt, (FunctionIR, EliminatedIR)):
                raise PassContractError(
                    f"Unexpected {type(stmt).__name__} in ClassIR body"
                )

        class_fields = [(field.name, field.type, field.default) for field in ir.fields]

        struct = StructIR(name=ir.name, class_fields=class_fields)

        init = self._find_init(functions)
        struct.initialize_function = self._class_initializer(ir, init)
        self.generated_functions[ir.name] = struct.initialize_function

        methods = [fn for fn in functions if fn is not init]
        return (struct, *methods)

    def _find_init(self, functions):
        for fn in functions:
            if fn.ast_name == "__init__":
                return fn
        return None

    def _class_initializer(self, ir, init):
        class_type = ClassType(ir.name)
        fn_name = self.ctx["id_alloc"].anon()

        body = [
            AssignIR(
                target=IdentifierIR(name="self"),
                value=NewIR(class_name=ir.name, type=class_type),
                type=class_type,
            ),
        ]

        if init is not None:
            body.extend(init.body)

        body.append(
            ReturnIR(value=VariableIR(name="self", type=class_type), type=class_type)
        )

        args = init.args[1:] if init is not None else []

        return FunctionIR(
            name=fn_name,
            args=args,
            body=body,
            type=class_type,
            is_main_func=False,
            is_static=True,
        )
