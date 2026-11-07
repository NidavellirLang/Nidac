from IR_gen.irs import *
from LIR_gen.lirs import *
from .c_nodes import *
from .c_types import *
from .extra_c_includes import EXTRA_C_INCLUDES
from type_systems.types import ClassType, RefType


class CExprTranslator:
    @classmethod
    def translate(cls, value):
        if isinstance(value, int):
            return CNumber(value)

        if isinstance(value, float):
            return CNumber(value)

        if isinstance(value, str):
            return CString(value)

        raise Exception(f"Unsupported expression value: {type(value).__name__}")


class CTypeTranslator:
    INT_TYPES = {
        "u8": CTInt(False, 1),
        "i8": CTInt(True, 1),
        "u16": CTInt(False, 2),
        "i16": CTInt(True, 2),
        "u32": CTInt(False, 4),
        "i32": CTInt(True, 4),
        "u64": CTInt(False, 8),
        "i64": CTInt(True, 8),
        "idyn": CTInt(True, 8),  # TODO: impl real dynamic int
    }

    FLOAT_TYPES = {
        "f32": CTFloat(4),
        "f64": CTFloat(8),
        "fdyn": CTFloat(8),  # TODO: impl real dynamic float
    }

    TYPES = {
        **INT_TYPES,
        **FLOAT_TYPES,
        "bool": CTInt(False, 1),
        "None": CTNone(),
        "str": CTString(),
        "List": CTList(CTVoid()),
        "Nida_List *": CTList(CTVoid()),
    }

    @classmethod
    def translate(cls, type_name) -> CType:
        if isinstance(type_name, ClassType):
            return CTStruct(type_name.name)

        try:
            return cls.TYPES[type_name]
        except Exception:
            if isinstance(type_name, str) and type_name.isidentifier():
                return CTStruct(type_name)

            if isinstance(type_name, RefType):
                param_types, return_type = type_name.get_types()

                param_c_types = [CTypeTranslator.translate(p) for p in param_types]
                return_c_type = CTypeTranslator.translate(return_type)
                return CTFuncRef(param_c_types, return_c_type)

            raise Exception(
                f"Unsupported C translation for type: {type_name}, {type(type_name)}"
            )


class C_Gen:
    def __init__(self, LIRs, extra_include=[]):
        self.LIRs = LIRs
        self.extra_include = extra_include
        self.c_nodes = []

    def name_maper(self, name):
        if name is None:
            return None

        if name[0] == "%":
            name = "v" + name[1:]
        return name

    def process_ArgLIR(self, lir):
        name = self.name_maper(lir.name)
        type = CTypeTranslator.translate(lir.type)
        return CArg(name, type)

    def process_FunctionLIR(self, lir):
        name = lir.name
        args = lir.args
        body = lir.body
        is_static = lir.is_static
        return_type = CTypeTranslator.translate(lir.type)

        args_nodes = []
        for arg in args:
            args_nodes.append(self.process(arg))

        body_nodes = []
        for b in body:
            body_nodes.append(self.process(b))

        return CFunction(name, name, args_nodes, body_nodes, return_type, is_static)

    def process_ConstLIR(self, lir):
        lir_name = self.name_maper(lir.name)
        if lir.value is None:
            val = CNone()
        else:
            val = CExprTranslator.translate(lir.value)

        type = CTypeTranslator.translate(lir.type)
        if isinstance(type, CTString):
            val = CCall("Nida_str_new", [val])

        return CAssign(lir_name, val, type)

    def _lir_to_op(self, lir_node):
        match type(lir_node):
            case _ if isinstance(lir_node, AddLIR):
                return "+"
            case _ if isinstance(lir_node, SubLIR):
                return "-"
            case _ if isinstance(lir_node, MulLIR):
                return "*"
            case _ if isinstance(lir_node, DivLIR):
                return "/"
            case _ if isinstance(lir_node, ModLIR):
                return "%"
            case _ if isinstance(lir_node, GtLIR):
                return ">"
            case _ if isinstance(lir_node, LtLIR):
                return "<"
            case _ if isinstance(lir_node, GeLIR):
                return ">="
            case _ if isinstance(lir_node, LeLIR):
                return "<="
            case _ if isinstance(lir_node, EqLIR):
                return "=="
            case _ if isinstance(lir_node, NeLIR):
                return "!="
            case _:
                raise Exception(
                    f"No operator string for LIR node {type(lir_node).__name__}"
                )

    def _bin_ops(self, lir):
        name = self.name_maper(lir.name)
        type = CTypeTranslator.translate(lir.type)
        left = lir.left_id
        right = lir.right_id

        left_val = self.name_maper(left)
        left = CVariable(left_val)
        right_val = self.name_maper(right)
        right = CVariable(right_val)

        op = self._lir_to_op(lir)

        bin_op = CBinaryOp(left, right, op)

        return CAssign(name, bin_op, type)

    def process_AddLIR(self, lir):
        return self._bin_ops(lir)

    def process_SubLIR(self, lir):
        return self._bin_ops(lir)

    def process_MulLIR(self, lir):
        return self._bin_ops(lir)

    def process_DivLIR(self, lir):
        return self._bin_ops(lir)

    def process_ModLIR(self, lir):
        return self._bin_ops(lir)

    def process_GtLIR(self, lir):
        return self._bin_ops(lir)

    def process_LtLIR(self, lir):
        return self._bin_ops(lir)

    def process_GeLIR(self, lir):
        return self._bin_ops(lir)

    def process_LeLIR(self, lir):
        return self._bin_ops(lir)

    def process_EqLIR(self, lir):
        return self._bin_ops(lir)

    def process_NeLIR(self, lir):
        return self._bin_ops(lir)

    def process_DeclareLIR(self, lir):
        name = lir.name
        type = CTypeTranslator.translate(lir.type)
        val_name = self.name_maper(lir.value)
        value = CVariable(val_name)
        return CAssign(name, value, type)

    def process_DeclareOnlyLIR(self, lir):
        name = lir.name
        type = CTypeTranslator.translate(lir.type)
        value = CNone(is_str=False)
        return CAssign(name, value, type)

    def process_StoreLIR(self, lir):
        name = lir.name
        type = CTypeTranslator.translate(lir.type)
        val_name = self.name_maper(lir.value)
        value = CVariable(val_name)
        return CAssign(name, value, type, re_assign=True)

    def process_CastLIR(self, lir):
        name = self.name_maper(lir.name)
        target_type = CTypeTranslator.translate(lir.target_type)
        value_name = self.name_maper(lir.value)

        cast = CCast(target_type, CVariable(value_name))
        return CAssign(name, cast, target_type)

    def process_ReturnLIR(self, lir):
        value = lir.value
        if value is None:
            return CReturn(CNone())

        val_name = self.name_maper(value)
        value = CVariable(val_name)
        return CReturn(value)

    def process_LoadLIR(self, lir):
        name = self.name_maper(lir.name)
        var_name = self.name_maper(lir.var_name)
        var = CVariable(var_name)
        return CAssign(name, var, CTypeTranslator.translate(lir.type))

    def process_CallLIR(self, lir):
        name = self.name_maper(lir.name)
        target = lir.func_name
        args = lir.args

        args_lirs = []
        for arg in args:
            mname = self.name_maper(arg)
            args_lirs.append(CVariable(mname))

        call = CCall(target, args_lirs)
        if name is None:
            return call
        else:
            assign = CAssign(name, call, CTypeTranslator.translate(lir.type))
            return assign

    def process_BlockLIR(self, lir):
        name = lir.name
        body = lir.body

        body_nodes = []
        for b in body:
            body_nodes.append(self.process(b))

        return CBlock(name, body_nodes)

    def process_JumpLIR(self, lir):
        target = lir.target_block
        return CGoto(target)

    def process_BranchLIR(self, lir):
        cond = lir.condition
        true_block = lir.true_block
        false_block = lir.false_block

        cond_id = self.name_maper(cond)
        else_body = [CGoto(false_block)] if false_block else None
        return CIf(cond_id, [CGoto(true_block)], None, else_body)

    def process_GlobalLIR(self, lir):
        name = lir.name
        type = CTypeTranslator.translate(lir.type)
        initializer = lir.initializer

        return CGlobal(name, type, initializer)

    def process_StructLIR(self, lir):
        fields = [
            CFieldDecl(f.name, CTypeTranslator.translate(f.type)) for f in lir.fields
        ]

        return CStruct(lir.name, fields)

    def process_FieldAccessLIR(self, lir):
        target = lir.target

        if isinstance(target, str):
            target = CVariable(self.name_maper(target))
        else:
            target = self.process(target)

        access = CFieldAccess(target, lir.field)

        return CAssign(
            self.name_maper(lir.name),
            access,
            CTypeTranslator.translate(lir.type),
        )

    def process_FieldStoreLIR(self, lir):
        target = CVariable(self.name_maper(lir.target))
        value = CVariable(self.name_maper(lir.value))

        return CFieldStore(target, lir.field, value)

    def process_NewLIR(self, lir):
        return CAssign(
            self.name_maper(lir.name),
            CNew(lir.class_name),
            CTypeTranslator.translate(lir.type),
        )

    def process_UnaryOpLIR(self, lir):
        name = self.name_maper(lir.name)
        type = CTypeTranslator.translate(lir.type)

        val_name = self.name_maper(lir.value)

        return CUnaryOp(name, lir.op, val_name, type)

    def process(self, lir):
        name = lir.__class__.__name__
        func = getattr(self, f"process_{name}", None)
        if func is None:
            raise Exception(f"No function named {name}")

        return func(lir)

    def include_name_map(self, name):
        if name.startswith('"'):
            return name
        elif name.startswith("<"):
            return name
        return f'"{name}"'

    def get_code_string(self):
        body_code = ""
        for idx, c_node in enumerate(self.c_nodes):
            if idx == 0:
                body_code += "\n" + c_node.str()
            else:
                body_code += ";\n" + c_node.str()

        includes = ["#include <Nida_core.h>"]
        for include in EXTRA_C_INCLUDES:
            includes.append(f"#include {self.include_name_map(include)}")

        for include in self.extra_include:
            incl = f"#include {self.include_name_map(include)}"
            if incl not in includes:
                includes.append(incl)

        return "\n".join(includes) + "\n" + body_code

    def gen_from_list(self, lirs):
        for lir in lirs:
            res = self.process(lir)
            if res is not None:
                self.c_nodes.append(res)

        return self.get_code_string()
