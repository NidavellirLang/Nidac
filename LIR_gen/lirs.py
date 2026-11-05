class LIR:
    def _format_item(self, item, indent=0):
        if isinstance(item, LIR):
            return item._format(indent)
        elif isinstance(item, list):
            return "\n".join([self._format_item(i, indent + 1) for i in item])
        else:
            return repr(item)

    def _format(self, indent=0):
        indent_str = ("  ") * (indent + 1)
        indent_str_parent = ("  ") * indent

        lines = []

        class_args = self.__dict__.items()
        class_name = self.__class__.__name__
        lines.append(f"{indent_str_parent}{class_name}:")

        for key, value in class_args:
            field_prefix = f"{key}: {self._format_item(value, indent + 1)}"
            lines.append(f"{indent_str}{field_prefix}")

        return "\n" + "\n".join(lines) + "\n"

    def __repr__(self):
        return self._format()


class ConstLIR(LIR):
    def __init__(self, name, type, value):
        self.name = name
        self.type = type
        self.value = value


class DeclareLIR(LIR):
    def __init__(self, name, type, value):
        self.name = name
        self.type = type
        self.value = value


class DeclareOnlyLIR:
    def __init__(self, name, type):
        self.name = name
        self.type = type


class StoreLIR(LIR):
    def __init__(self, name, type, value):
        self.name = name
        self.type = type
        self.value = value


class LoadLIR(LIR):
    def __init__(self, name, var_name, type):
        self.name = name
        self.var_name = var_name
        self.type = type


class FunctionLIR(LIR):
    def __init__(self, name, args, type, body, is_static):
        self.name = name
        self.args = args
        self.type = type
        self.is_static = is_static
        self.body = body


class ReturnLIR(LIR):
    def __init__(self, value):
        self.value = value


class AddLIR(LIR):
    def __init__(self, name, type, left_id, right_id):
        self.name = name
        self.type = type
        self.left_id = left_id
        self.right_id = right_id


class SubLIR(LIR):
    def __init__(self, name, type, left_id, right_id):
        self.name = name
        self.type = type
        self.left_id = left_id
        self.right_id = right_id


class MulLIR(LIR):
    def __init__(self, name, type, left_id, right_id):
        self.name = name
        self.type = type
        self.left_id = left_id
        self.right_id = right_id


class DivLIR(LIR):
    def __init__(self, name, type, left_id, right_id):
        self.name = name
        self.type = type
        self.left_id = left_id
        self.right_id = right_id


class ModLIR(LIR):
    def __init__(self, name, type, left_id, right_id):
        self.name = name
        self.type = type
        self.left_id = left_id
        self.right_id = right_id


class GtLIR(LIR):
    def __init__(self, name, type, left_id, right_id):
        self.name = name
        self.type = type
        self.left_id = left_id
        self.right_id = right_id


class LtLIR(LIR):
    def __init__(self, name, type, left_id, right_id):
        self.name = name
        self.type = type
        self.left_id = left_id
        self.right_id = right_id


class GeLIR(LIR):
    def __init__(self, name, type, left_id, right_id):
        self.name = name
        self.type = type
        self.left_id = left_id
        self.right_id = right_id


class LeLIR(LIR):
    def __init__(self, name, type, left_id, right_id):
        self.name = name
        self.type = type
        self.left_id = left_id
        self.right_id = right_id


class IsLIR(LIR):
    def __init__(self, name, type, left_id, right_id):
        self.name = name
        self.type = type
        self.left_id = left_id
        self.right_id = right_id


class IsNotLIR(LIR):
    def __init__(self, name, type, left_id, right_id):
        self.name = name
        self.type = type
        self.left_id = left_id
        self.right_id = right_id


class EqLIR(LIR):
    def __init__(self, name, type, left_id, right_id):
        self.name = name
        self.type = type
        self.left_id = left_id
        self.right_id = right_id


class NeLIR(LIR):
    def __init__(self, name, type, left_id, right_id):
        self.name = name
        self.type = type
        self.left_id = left_id
        self.right_id = right_id


class CallLIR(LIR):
    def __init__(self, name, type, func_name, args):
        self.name = name
        self.type = type
        self.func_name = func_name
        self.args = args


class ArgLIR(LIR):
    def __init__(self, name, type):
        self.name = name
        self.type = type


class BlockLIR(LIR):
    def __init__(self, name):
        self.name = name
        self.body = []
        self.terminator = None


class JumpLIR(LIR):
    def __init__(self, target_block):
        self.target_block = target_block


class BranchLIR(LIR):
    def __init__(self, condition, true_block, false_block=None):
        self.condition = condition
        self.true_block = true_block
        self.false_block = false_block


class GlobalLIR(LIR):
    def __init__(self, name, type, initializer):
        self.name = name
        self.type = type
        self.initializer = initializer


class StructLIR(LIR):
    def __init__(self, name, fields):
        self.name = name
        self.fields = fields


class FieldDeclLIR(LIR):
    def __init__(self, name, type):
        self.name = name
        self.type = type


class FieldAccessLIR(LIR):
    def __init__(self, name, target, field, type=None):
        self.name = name
        self.target = target
        self.field = field
        self.type = type


class FieldStoreLIR(LIR):
    def __init__(self, name, target, field, type, value):
        self.name = name
        self.target = target
        self.field = field
        self.type = type
        self.value = value


class NewLIR(LIR):
    def __init__(self, name, class_name, type=None):
        self.name = name
        self.class_name = class_name
        self.type = type


class UnaryOpLIR(LIR):
    def __init__(self, name, op, value, type=None):
        self.name = name
        self.op = op
        self.value = value
        self.type = type


class CastLIR:
    def __init__(self, name, target_type, value):
        self.name = name
        self.target_type = target_type
        self.value = value


class FieldRefLIR(LIR):
    def __init__(self, name, target, field, type):
        self.name = name
        self.target = target
        self.field = field
        self.type = type


class DeclareRefLIR(LIR):
    def __init__(self, name, type, ref):
        self.name = name
        self.type = type
        self.ref = ref
