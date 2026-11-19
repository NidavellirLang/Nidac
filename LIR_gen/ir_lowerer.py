from IR_gen.irs import *
from .lirs import *
from type_systems.types import *
from .operator_rules import *


class LIRs(list):
    def __init__(self, *args):
        super().__init__()

        for arg in args:
            self.append(arg)

    def append(self, item):
        if isinstance(item, list):
            super().extend(item)
        else:
            super().append(item)


class Value_Id:
    def __init__(self, parrent=None):
        self.value = -1
        self.parrent = parrent

    def new(self):
        self.value += 1
        return self.value

    def current(self):
        return self.value


class BlockBox:
    def __init__(self, block, parent=None):
        self.block = block
        self.parent = parent


class BlockManager:
    def __init__(self):
        self.blocks = []
        self.current = None
        self.block_id = Value_Id()

    def create_block(self, name=None):
        bname = name if name else f"B{self.block_id.new()}"

        parent_ctx = self.current.block.block_ctx if self.current is not None else None

        block = BlockLIR(bname)
        block.block_ctx = BlockContext(parent=parent_ctx)

        box = BlockBox(block, self.current)
        self.blocks.append(box)

        return block

    def new_block(self, name=None):
        block = self.create_block(name)
        self.switch_to(block)
        return block

    def switch_to(self, block):
        for box in self.blocks:
            if box.block is block or box.block.name == getattr(block, "name", block):
                self.current = box
                return box
        box = BlockBox(block, self.current)
        self.blocks.append(box)
        self.current = box
        return box

    def is_terminated(self):
        return self.current is not None and self.current.block.terminator is not None

    def emit(self, lir):
        if self.current is None:
            raise Exception("No active block")

        if self.current.block.terminator is not None:
            return

        if isinstance(lir, list):
            for item in lir:
                self.emit(item)
        elif lir is not None:
            self.current.block.body.append(lir)

    def terminate(self, terminator):
        if self.current is None:
            raise Exception("No active block")

        if self.current.block.terminator is not None:
            return

        self.current.block.terminator = terminator
        self.current.block.body.append(terminator)

    def branch(self, condition, true_block, false_block=None):
        true_name = true_block.name if hasattr(true_block, "name") else true_block
        false_name = false_block.name if hasattr(false_block, "name") else false_block
        self.terminate(BranchLIR(condition, true_name, false_name))

    def jump(self, target_block):
        target_name = (
            target_block.name if hasattr(target_block, "name") else target_block
        )
        self.terminate(JumpLIR(target_name))


class IRLowerer:
    def __init__(self, hirs):
        self.hir = hirs
        self.blocks = BlockManager()
        self.value_id = Value_Id()
        self.lir = []
        self.globals = []

        self.class_names = set()

        for hir in hirs:
            if isinstance(hir, (ClassIR, StructIR)):
                self.class_names.add(hir.name)

    def enter_new_value_scope(self):
        self.value_id = Value_Id(self.value_id)

    def exit_value_scope(self):
        if self.value_id.parrent is None:
            raise Exception("No parent value scope")

        self.value_id = self.value_id.parrent

    def get_value_id(self):
        id = self.value_id.new()
        return f"%{id}"

    def get_current_value_id(self):
        return f"%{self.value_id.current()}"

    def get_block_id(self):
        id = self.value_id.new()
        return f"B{id}"

    def get_current_block_id(self):
        return f"B{self.value_id.current()}"

    def process_StringLiteralIR(self, hir):
        lirs = LIRs()
        const_lir = ConstLIR(self.get_value_id(), "str", hir.value)
        self.blocks.emit(const_lir)
        lirs.append(const_lir)
        return lirs

    def process_VariableIR(self, hir):
        name = hir.name
        try:
            type_str = self.str_of(hir)
        except:
            raise Exception(hir.type)

        const_id = self.get_value_id()
        lirs = LIRs()
        load_lir = LoadLIR(const_id, name, type_str)
        lirs.append(load_lir)
        self.blocks.emit(load_lir)

        return lirs

    def process_FunctionRefIR(self, hir):
        lir = FunctionRefLIR(
            self.get_value_id(),
            self.type_of(hir),
            hir.name,
        )
        self.blocks.emit(lir)
        return lir

    def process_NumberIR(self, hir):
        val = hir.value
        types = self.type_of(hir)
        if val is not None and isinstance(val, str):
            if isinstance(types, FloatType):
                val = float(val)
            elif isinstance(types, IntType):
                val = int(val)
            else:
                raise Exception(f"Invalid number type: {hir.type}")

        const_id = self.get_value_id()
        type_str = self.type_to_str(types)
        const_lir = ConstLIR(const_id, type_str, val)
        self.blocks.emit(const_lir)

        return const_lir

    def process_ReturnIR(self, hir):
        lirs = LIRs()
        val = hir.value
        if val is None:
            ret_lir = ReturnLIR(None)
            self.blocks.terminate(ret_lir)
            return ret_lir

        val_lirs = self.process(val)
        ret_lir = ReturnLIR(self.get_current_value_id())

        lirs.append(val_lirs)
        lirs.append(ret_lir)
        self.blocks.terminate(ret_lir)

        return lirs

    def process_AssignIR(self, hir):
        lirs = LIRs()

        target = hir.target
        value = hir.value
        type_str = self.str_of(hir)

        is_no_value = isinstance(value, NoneIR) and value.air

        value_lirs = None
        value_id = None

        if not is_no_value:
            value_lirs = self.process(value)
            value_id = self.get_current_value_id()

        if isinstance(target, FieldAccessIR):
            if is_no_value:
                raise ValueError("Cannot assign to member without value")

            self.process(target.target)
            base_id = self.get_current_value_id()

            member_type = self.type_str_of(
                self.type_of(target),
                type_str,
            )

            as_lir = FieldStoreLIR(
                self.get_value_id(),
                base_id,
                target.field,
                member_type,
                value_id,
            )

        elif isinstance(target, IdentifierIR):
            if hir.re_assign:
                as_lir = StoreLIR(
                    target.name,
                    type_str,
                    value_id,
                )
            elif is_no_value:
                as_lir = DeclareOnlyLIR(target.name, type_str)
            else:
                as_lir = DeclareLIR(target.name, type_str, value_id)

        else:
            raise TypeError(f"Unsupported assignment target: {type(target).__name__}")

        self.blocks.emit(as_lir)

        if value_lirs is not None:
            lirs.append(value_lirs)

        lirs.append(as_lir)
        return lirs

    def _base_of(self, lirs):
        """The variable the last load in 'lirs' read from."""
        if isinstance(lirs, list):
            for l in reversed(lirs):
                if isinstance(l, LoadLIR):
                    return l.var_name

        return None

    def _load_base(self, target, base_type=None):
        self.process(VariableIR(target, base_type))
        return self.get_current_value_id()

    def process_args(self, args):
        args_lir = LIRs()
        arg_loads = LIRs()

        for arg in args:
            value_id = self.get_value_id()
            type_str = self.str_of(arg)

            args_lir.append(ArgLIR(value_id, type_str))
            arg_loads.append(LoadLIR(arg.name, value_id, type_str))

        return args_lir, arg_loads

    def process_FunctionIR(self, hir):
        self.enter_new_value_scope()

        name = hir.name
        args = hir.args
        is_static = hir.is_static
        try:
            type_str = self.str_of(hir)
        except:
            raise Exception(hir)
        body = hir.body

        prev_blocks = self.blocks
        self.blocks = BlockManager()

        self.blocks.new_block()

        args_lir, arg_load = self.process_args(args)
        self.blocks.emit(arg_load)

        for stmt in body:
            self.process(stmt)

        if (
            self.blocks.current
            and not self.blocks.is_terminated()
            and isinstance(hir.type, NoneType)
        ):
            self.blocks.terminate(ReturnLIR(None))

        fn_blocks = [box.block for box in self.blocks.blocks]

        self.blocks = prev_blocks
        self.exit_value_scope()

        return FunctionLIR(name, args_lir, type_str, fn_blocks, is_static)

    def process_GroupIR(self, hir):
        return self.process(hir.expr)

    def process_ListLiteralIR(self, hir):
        lirs = LIRs()

        lirs.append(self._runtime_call("Nida_list_new", [], "Nida_List *"))

        tmp_name = f"__nida_list_{hir.element_list_id}"

        declare_lir = DeclareLIR(tmp_name, "Nida_List *", self.get_current_value_id())
        self.blocks.emit(declare_lir)
        lirs.append(declare_lir)

        for element in hir.elements:
            lirs.append(self.process(element))

            lirs.append(
                self._runtime_call(
                    "Nida_list_append",
                    [tmp_name, self.get_current_value_id()],
                    "void",
                )
            )

        load_lir = LoadLIR(self.get_value_id(), tmp_name, "Nida_List *")
        self.blocks.emit(load_lir)
        lirs.append(load_lir)

        return lirs

    def _runtime_call(self, func_name, arg_ids, return_type):
        """Emit a direct C runtime call; the value id only exists when it returns."""
        value_id = None if return_type == "void" else self.get_value_id()
        call_lir = CallLIR(value_id, return_type, func_name, arg_ids)

        self.blocks.emit(call_lir)

        lirs = LIRs()
        lirs.append(call_lir)

        return lirs

    def process_CallIR(self, hir):
        lirs = LIRs()
        args = hir.args

        if getattr(hir, "runtime_call", False):
            arg_ids = []

            for arg in args:
                lirs.append(self.process(arg))
                arg_ids.append(self.get_current_value_id())

            return_type = self.type_str_of(self.type_of(hir), "None")

            if isinstance(self.type_of(hir), NoneType) or return_type == "None":
                return_type = "void"

            lirs.append(self._runtime_call(hir.target, arg_ids, return_type))
            return lirs

        target = hir.target

        receiver = None
        field = None
        func_type = None

        if isinstance(target, IdentifierIR):
            call_target = target.name
        elif isinstance(target, FieldAccessIR):
            if getattr(hir, "indirect", False):
                lirs.append(self.process(target.target))
                receiver = self.get_current_value_id()
                field = target.field
                func_type = target.type
            call_target = target.field
        else:
            raise TypeError(f"Invalid call target: {type(target).__name__}")

        arg_ids = []

        for arg in args:
            lirs.append(self.process(arg))
            arg_ids.append(self.get_current_value_id())

        type_str = self.str_of(hir)
        is_not_return = (
            isinstance(self.type_of(hir), NoneType) or self.type_of(hir) is None
        )

        if is_not_return:
            const_lir = ConstLIR(self.get_value_id(), str(NoneType()), None)
            self.blocks.emit(const_lir)
            lirs.append(const_lir)

        call_lir = CallLIR(
            None if is_not_return else self.get_value_id(),
            type_str,
            call_target,
            arg_ids,
            receiver=receiver,
            field=field,
            func_type=func_type,
        )

        self.blocks.emit(call_lir)
        lirs.append(call_lir)
        return lirs

    def _coerce_numeric(self, value_id, source_type, target_type):
        if source_type is None or target_type is None:
            return value_id

        if type(source_type) is type(target_type):
            return value_id

        if not isinstance(source_type, NumberType):
            return value_id

        if not isinstance(target_type, NumberType):
            return value_id

        cast_id = self.get_value_id()
        cast_lir = CastLIR(cast_id, self.type_to_str(target_type), value_id)
        self.blocks.emit(cast_lir)

        return cast_id

    def _get_operator_rules(self, typex):
        if isinstance(typex, StringType):
            return STR_OPS

        # TODO: impl dynamic int/float
        # if isinstance(typex, IntType) and typex.is_dynamic:
        #     return IDYN_OPS

        # if isinstance(typex, FloatType) and typex.is_dynamic:
        #     return FDYN_OPS

        return INT_OPS

    def _op_to_lir(self, typex, left_id, right_id, op):
        rules = self._get_operator_rules(typex)
        rule = rules.get(op)

        if rule is None:
            raise Exception(f"Unsupported operator: {typex} {op}")

        result_id = self.get_value_id()
        result_type = rule.result_type or self.type_to_str(typex)

        if rule.runtime is not None:
            return CallLIR(
                result_id,
                result_type,
                rule.runtime,
                [left_id, right_id],
            )

        return rule.instruction(
            result_id,
            result_type,
            left_id,
            right_id,
        )

    def process_BinaryOpIR(self, hir):
        left = hir.left
        right = hir.right
        result_type = self.type_of(hir)
        op = hir.op

        lirs = LIRs()

        left_lir = self.process(left)
        left_id = self.get_current_value_id()

        right_lir = self.process(right)
        right_id = self.get_current_value_id()

        left_type = self.type_of(left)
        right_type = self.type_of(right)

        if op == "/" and isinstance(result_type, FloatType):
            left_id = self._coerce_numeric(left_id, left_type, result_type)
            right_id = self._coerce_numeric(right_id, right_type, result_type)

        op_lir = self._op_to_lir(
            result_type,
            left_id,
            right_id,
            op,
        )
        self.blocks.emit(op_lir)

        lirs.append(left_lir)
        lirs.append(right_lir)
        lirs.append(op_lir)

        return lirs

    def process_BooleanIR(self, hir):
        value = hir.value
        val = 1 if value else 0
        const_lir = ConstLIR(self.get_value_id(), "bool", val)
        self.blocks.emit(const_lir)
        return const_lir

    def process_BlockIR(self, hir):
        lirs = self.process_from_list(hir.body)
        return lirs

    def process_IfIR(self, hir):
        merge_block = self.blocks.create_block()

        has_else_path = bool(hir.elifs) or hir.else_body is not None
        false_target = self.blocks.create_block() if has_else_path else merge_block

        self.process(hir.cond)
        cond_id = self.get_current_value_id()

        then_block = self.blocks.create_block()
        self.blocks.branch(cond_id, then_block, false_target)

        self.blocks.switch_to(then_block)
        self._lower_branch_body(hir.body, merge_block)

        if has_else_path:
            self._lower_else_chain(hir.elifs, hir.else_body, false_target, merge_block)

        self.blocks.switch_to(merge_block)

    def process_WhileIR(self, hir):
        is_always_true = isinstance(hir.cond, BooleanIR) and hir.cond.value

        cond_block = self.blocks.create_block()
        loop_block = self.blocks.create_block()
        merge_block = self.blocks.create_block()

        self.blocks.jump(cond_block)

        self.blocks.switch_to(cond_block)
        self.process(hir.cond)

        if not is_always_true:
            cond_id = self.get_current_value_id()
            self.blocks.branch(cond_id, loop_block, merge_block)
        else:
            self.blocks.jump(loop_block)

        self.blocks.switch_to(loop_block)

        ctx = self.blocks.current.block.block_ctx
        ctx.loop_id = hir.node_id
        ctx.break_target = merge_block
        ctx.continue_target = cond_block

        self.process_from_list(hir.body)

        if not self.blocks.is_terminated():
            self.blocks.jump(cond_block)

        self.blocks.switch_to(merge_block)

    def process_BreakIR(self, hir):
        ctx = self.blocks.current.block.block_ctx

        while ctx is not None:
            if ctx.break_target is not None:
                self.blocks.jump(ctx.break_target)
                return

            ctx = ctx.parent

        raise RuntimeError("break outside loop")

    def process_ForIR(self, hir):
        # The First block
        target = hir.target.target
        target_reassign = hir.target.re_assign
        source = hir.source

        if not isinstance(source, RangeIR):
            raise NotImplementedError("Only range-based for loops are supported")

        target_type = self.type_to_str(hir.target.type or source.end.type)
        hir.target.type = source.end.type

        source.start.type = hir.target.type
        source.end.type = hir.target.type
        source.step.type = hir.target.type

        condition_block = self.blocks.create_block()
        loop_block = self.blocks.create_block()
        merge_block = self.blocks.create_block()

        self.process(source.start)
        if target_reassign:
            self.blocks.emit(StoreLIR(target, target_type, self.get_current_value_id()))
        else:
            self.blocks.emit(
                DeclareLIR(target, target_type, self.get_current_value_id())
            )
        self.blocks.jump(condition_block)

        # The condition block

        self.blocks.switch_to(condition_block)
        self.blocks.emit(LoadLIR(self.get_value_id(), target, target_type))
        loaded_id = self.get_current_value_id()
        self.process(source.end)
        end_id = self.get_current_value_id()
        self.blocks.emit(LtLIR(self.get_value_id(), target_type, loaded_id, end_id))
        self.blocks.branch(self.get_current_value_id(), loop_block, merge_block)

        # The loop block
        self.blocks.switch_to(loop_block)

        self.process_from_list(hir.body)

        self.process(source.step)
        step_id = self.get_current_value_id()
        self.blocks.emit(LoadLIR(self.get_value_id(), target, target_type))

        loaded_id = self.get_current_value_id()
        self.blocks.emit(AddLIR(self.get_value_id(), target_type, loaded_id, step_id))
        self.blocks.emit(StoreLIR(target, target_type, self.get_current_value_id()))
        self.blocks.jump(condition_block)

        self.blocks.switch_to(merge_block)

    def _lower_branch_body(self, body, merge_block):
        if isinstance(body, BlockIR):
            body = body.body

        for stmt in body:
            self.process(stmt)

        if not self.blocks.is_terminated():
            self.blocks.jump(merge_block)

    def _lower_else_chain(self, elifs, else_body, current_false_block, merge_block):
        if elifs:
            for idx, elif_ir in enumerate(elifs):
                is_last = idx == len(elifs) - 1
                next_false = (
                    self.blocks.create_block()
                    if (not is_last or else_body is not None)
                    else merge_block
                )

                self.blocks.switch_to(current_false_block)
                self.process(elif_ir.cond)
                cond_id = self.get_current_value_id()

                elif_then = self.blocks.create_block()
                self.blocks.branch(cond_id, elif_then, next_false)

                self.blocks.switch_to(elif_then)
                self._lower_branch_body(elif_ir.body, merge_block)

                current_false_block = next_false

        if else_body is not None:
            self.blocks.switch_to(current_false_block)
            self._lower_branch_body(else_body, merge_block)

    def process_IRImport(self, hir):
        module = hir.resolved_module
        if module is None:
            return

        hirs = module.hirs
        lirs = IRLowerer(hirs).run()
        module.lirs = lirs
        return

    def process_DefinitionIR(self, hir):
        target = hir.target
        value = hir.value
        type_str = self.str_of(hir)

        init_fn = hir.initializer

        gl_lir = GlobalLIR(target, type_str, init_fn)
        self.globals.append(gl_lir)

        # Do not append to lirs because it is not a statement.
        return None

    def process_StructIR(self, hir):
        fields = []
        # raise Exception(hir)
        for name, field_type, _ in hir.class_fields:
            try:
                self.type_to_str(field_type)
            except:
                raise Exception(hir)

            fields.append(FieldDeclLIR(name, self.type_to_str(field_type)))

        struct_lir = StructLIR(hir.name, fields)

        init = hir.initialize_function

        if init is not None:
            init_lir = self.process(init)

            if isinstance(init_lir, FunctionLIR):
                self.lir.append(init_lir)

        return struct_lir

    def process_NewIR(self, hir):
        new_lir = NewLIR(
            self.get_value_id(), hir.class_name, self.type_to_str(self.type_of(hir))
        )
        self.blocks.emit(new_lir)

        return new_lir

    def process_UnaryOpIR(self, hir):
        op = hir.op

        value_lirs = self.process(hir.value)
        value_id = self.get_current_value_id()

        type_str = self.str_of(hir)
        result_id = self.get_value_id()

        lir = UnaryOpLIR(result_id, op, value_id, type_str)
        self.blocks.emit(lir)

        lirs = LIRs()
        lirs.append(value_lirs)
        lirs.append(lir)

        return lirs

    def process_FieldAccessIR(self, hir):
        target_lir = self.process(hir.target)
        target_id = self.get_current_value_id()
        type_str = self.str_of(hir)

        result_id = self.get_value_id()
        lir = FieldAccessLIR(result_id, target_id, hir.field, type_str)
        self.blocks.emit(lir)

        return lir

    def process_PassIR(self, hir):
        pass

    def process_EliminatedIR(self, hir):
        pass

    def process_StmtExprIR(self, hir):
        return self.process(hir.expr)

    def process(self, hir):
        name = hir.__class__.__name__
        func = getattr(self, f"process_{name}", None)
        if func is None:
            raise Exception(f"No process function for {name}")

        return func(hir)

    def process_from_list(self, hirs):
        lirs = LIRs()
        for hir in hirs:
            res = self.process(hir)
            if res is not None:
                lirs.append(res)

        return lirs

    def run(self):
        if self.blocks.current is None:
            self.blocks.new_block()

        structs = []

        for hir in self.hir:
            res = self.process(hir)
            if isinstance(res, StructLIR):
                structs.append(res)
            elif isinstance(res, FunctionLIR):
                self.lir.append(res)

        for box in self.blocks.blocks:
            if box.parent is None or box.parent.block in self.lir:
                if box.block not in self.lir and box.block.body:
                    self.lir.append(box.block)

        # Structs come first: a function may use the type they define.
        return [*self.globals, *structs, *self.lir]

    def type_str_of(self, type_val, fallback=None):
        if type_val is None:
            return fallback

        if isinstance(type_val, Type):
            return self.type_to_str(type_val)

        resolved = resolve_type(type_val)

        if resolved is not None:
            return str(resolved)

        if isinstance(type_val, str) and type_val in self.class_names:
            return str(ClassType(type_val))

        return str(type_val)

    def type_to_str(self, type_val):
        if isinstance(type_val, (RefType, FuncPtrType)):
            return type_val

        if isinstance(type_val, Type):
            return str(type_val)

        raise Exception(f"Invalid type: {type_val}, {type(type_val)}")

    def str_of(self, hir):
        type = self.type_of(hir)
        return self.type_to_str(type)

    def type_of(self, hir):
        type_val = getattr(hir, "type", None)

        if type_val is None or isinstance(type_val, Type):
            return type_val

        if isinstance(type_val, FuncRefType):
            return type_val

        resolved = resolve_type(type_val)

        if resolved is not None:
            return resolved

        if isinstance(type_val, str) and type_val in self.class_names:
            return ClassType(type_val)

        return type_val
