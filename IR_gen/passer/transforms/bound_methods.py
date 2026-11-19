from ..transformer import IRTransform
from ...irs import *
from type_systems.types import BoundMethodType, ClassType, FuncPtrType, NoneType


class BoundMethods(IRTransform):
    def __init__(self):
        self.pending = []
        self.struct = None
        self.initializer = None
        self.struct_type = None
        self.fn_type = FuncPtrType([], NoneType())
        self.self_type = NoneType()

    def run(self, node, ctx=None):
        self.pending = []
        self.struct = None
        self.initializer = None
        self.struct_type = None

        node = super().run(node, ctx)
        node.body[:0] = self.pending
        return node

    def visit(self, ir):
        if isinstance(ir, AssignIR) and isinstance(ir.type, BoundMethodType):
            return self.process_assign(ir)

        if isinstance(ir, BoundCallIR):
            return self.process_bound_call(ir)

        if isinstance(ir, (FunctionIR, ReturnIR, ParameterIR, VariableIR, IdentifierIR)):
            if isinstance(ir.type, BoundMethodType):
                self.create_bound_reqs()
                ir.type = self.struct_type
                self.changed = True

        return ir

    def process_assign(self, ir):
        self.create_bound_reqs()

        value = ir.value

        if isinstance(value, BoundMethodIR):
            ir.value = CallIR(
                target=IdentifierIR(name=self.initializer.name),
                args=[
                    value.receiver,
                    FunctionRefIR(name=value.method, type=self.fn_type),
                ],
                type=self.struct_type,
                node_id=ir.node_id,
            )
        else:
            value.type = self.struct_type

        ir.type = self.struct_type

        self.changed = True
        return ir

    def process_bound_call(self, ir):
        self.create_bound_reqs()

        bound = ir.bound
        ref = getattr(ir, "ref", None) or getattr(bound.type, "ref", None)
        self_type = self.instance_type(ref)
        fn_type = ref if ref is not None else self.fn_type

        receiver = FieldAccessIR(
            target=VariableIR(name=bound.name, type=self.struct_type),
            field="self",
            type=self_type,
        )
        fn = FieldAccessIR(
            target=VariableIR(name=bound.name, type=self.struct_type),
            field="fn",
            type=fn_type,
        )

        self.changed = True
        return CallIR(
            target=fn,
            args=[receiver, *ir.args],
            type=ir.type,
            indirect=True,
            node_id=ir.node_id,
        )

    def instance_type(self, ref):
        instance_lk = getattr(ref, "instance_lk", None)
        instance_type = getattr(instance_lk, "type", None)

        if isinstance(instance_type, ClassType):
            return instance_type

        return self.self_type

    def create_bound_reqs(self):
        if self.struct is not None:
            return

        struct_name = self.ctx["id_alloc"].anon()
        self.struct_type = ClassType(struct_name)

        self.struct = StructIR(
            name=struct_name,
            class_fields=[
                ("self", self.self_type, None),
                ("fn", self.fn_type, None),
            ],
        )

        tmp = self.ctx["id_alloc"].anon()

        body = [
            AssignIR(
                target=IdentifierIR(name=tmp),
                value=NewIR(class_name=struct_name, type=self.struct_type),
                type=self.struct_type,
            ),
            AssignIR(
                target=FieldAccessIR(
                    target=VariableIR(name=tmp, type=self.struct_type),
                    field="self",
                    type=self.self_type,
                ),
                value=VariableIR(name="self", type=self.self_type),
                type=self.self_type,
            ),
            AssignIR(
                target=FieldAccessIR(
                    target=VariableIR(name=tmp, type=self.struct_type),
                    field="fn",
                    type=self.fn_type,
                ),
                value=VariableIR(name="fn", type=self.fn_type),
                type=self.fn_type,
            ),
            ReturnIR(
                value=VariableIR(name=tmp, type=self.struct_type),
                type=self.struct_type,
            ),
        ]

        self.initializer = FunctionIR(
            name=self.ctx["id_alloc"].anon(),
            args=[
                ParameterIR(name="self", type=self.self_type),
                ParameterIR(name="fn", type=self.fn_type),
            ],
            body=body,
            type=self.struct_type,
            is_static=True,
        )

        self.pending.append(self.struct)
        self.pending.append(self.initializer)
