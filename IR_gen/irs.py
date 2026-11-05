class IR:
    def tree_repr(self, indent="", is_last=True):
        if self.__class__.__name__ == "VariableIR":
            return f"{indent}{'└── ' if is_last else '├── '}VariableIR({repr(getattr(self, 'name', ''))})"
        if self.__class__.__name__ == "NumberIR":
            return f"{indent}{'└── ' if is_last else '├── '}NumberIR({repr(getattr(self, 'value', ''))})"

        marker = "└── " if is_last else "├── "
        lines = [f"{indent}{marker}{self.__class__.__name__}"]

        children = []
        for k, v in self.__dict__.items():
            if k in ("decs") and not v:
                continue
            children.append((k, v))

        child_indent = indent + ("    " if is_last else "│   ")

        for i, (key, val) in enumerate(children):
            is_last_child = i == len(children) - 1
            c_marker = "└── " if is_last_child else "├── "

            if isinstance(val, IR):
                lines.append(f"{child_indent}{c_marker}{key}:")
                lines.append(
                    val.tree_repr(
                        indent=child_indent + ("    " if is_last_child else "│   "),
                        is_last=True,
                    )
                )
            elif "Symbol" in val.__class__.__name__:
                lines.append(
                    f"{child_indent}{c_marker}{key}: <NidaSym: {val.__class__.__name__}>"
                )
            elif isinstance(val, list):
                if not val:
                    lines.append(f"{child_indent}{c_marker}{key}: []")
                    continue
                lines.append(f"{child_indent}{c_marker}{key}:")
                list_indent = child_indent + ("    " if is_last_child else "│   ")
                for j, item in enumerate(val):
                    is_last_item = j == len(val) - 1
                    if isinstance(item, IR):
                        lines.append(
                            item.tree_repr(indent=list_indent, is_last=is_last_item)
                        )
                    else:
                        item_marker = "└── " if is_last_item else "├── "
                        lines.append(f"{list_indent}{item_marker}{repr(item)}")
            else:
                lines.append(f"{child_indent}{c_marker}{key}: {repr(val)}")

        return "\n".join(lines)

    def __repr__(self):
        return self.tree_repr()


class PassIR(IR):
    pass


class AssignIR(IR):
    def __init__(
        self,
        target,
        value,
        type=None,
        re_assign=False,
        field=None,
    ):
        self.target = target
        self.value = value
        self.type = type

        self.re_assign = re_assign
        self.field = field


class FieldAccessIR(IR):
    def __init__(self, target, field, type=None):
        self.target = target
        self.field = field
        self.type = type


class FunctionIR(IR):
    def __init__(
        self,
        decs,
        name,
        args,
        body,
        type=None,
        is_main_func=False,
        is_static=False,
        ast_name=None,
    ):
        self.decs = decs
        self.name = name
        self.args = args
        self.body = body
        self.type = type

        self.is_static = is_static

        self.is_main_func = is_main_func

        # The name in the source, before it was turned into an id.
        self.ast_name = ast_name


class NewIR(IR):
    """Allocates an instance of a class."""

    def __init__(self, class_name, type=None):
        self.class_name = class_name
        self.type = type


class ReturnIR(IR):
    def __init__(self, value, type=None):
        self.value = value
        self.type = None


class BinaryOpIR(IR):
    def __init__(self, left, right, op, type=None):
        self.left = left
        self.right = right
        self.op = op
        self.type = type


class VariableIR(IR):
    def __init__(self, name, type=None):
        self.name = name
        self.type = type

        self.target = name


class CallIR(IR):
    def __init__(self, target, args, type=None, field=None):
        self.target = target
        self.args = args
        self.type = type

        self.field = field

        self.imported_func_call = False

        self.runtime_call = False


class NumberIR(IR):
    def __init__(self, value, type=None):
        self.value = value
        self.type = type


class ClassIR(IR):
    def __init__(self, name, id, body, fields=None):
        self.name = name
        self.body = body

        # The declared fields of the class: [(name, type, default_value)].
        self.fields = fields or []


class StringLiteralIR(IR):
    def __init__(self, value):
        self.value = value


class IRImport(IR):
    def __init__(
        self,
        module: str,
        symbols: list[str] = None,
        alias: str = None,
        resolved_module=None,
    ):
        self.module = module
        self.symbols = symbols or []
        self.alias = alias
        self.resolved_module = resolved_module


class IfIR(IR):
    def __init__(self, cond, body, elifs, else_body, if_sym):
        self.cond = cond
        self.body = body
        self.elifs = elifs
        self.else_body = else_body
        self.if_sym = if_sym


class ElifIR(IR):
    def __init__(self, cond, body):
        self.cond = cond
        self.body = body


class BlockIR(IR):
    def __init__(self, body):
        self.body = body


class GroupIR(IR):
    def __init__(self, expr):
        self.expr = expr


class ForIR(IR):
    def __init__(self, target, source, body):
        self.target = target
        self.source = source
        self.body = body


class WhileIR(IR):
    def __init__(self, cond, body):
        self.cond = cond
        self.body = body


class BooleanIR(IR):
    def __init__(self, value):
        self.value = value


class NoneIR(IR):
    def __init__(self, air=True):
        self.air = air


class IntrinsicCallIR(IR):
    def __init__(self, intrinsic, name, args, type):
        self.intrinsic = intrinsic
        self.name = name
        self.args = args
        self.type = type


class DefinitionIR(IR):
    def __init__(self, target, value, type):
        self.target = target
        self.value = value
        self.type = type

        self.initializer = None


class RangeIR(IR):
    def __init__(self, start, end, step):
        self.start = start
        self.end = end
        self.step = step


# only use for ir_passer
class StructIR(IR):
    def __init__(self, name, fields: list[AssignIR], class_fields=None):
        self.name = name
        self.fields = fields

        # The physical layout of the struct: [(name, type, default_value)].
        self.class_fields = class_fields or []

        self.initialize_function = None


class UnaryOpIR(IR):
    def __init__(self, op, value, type=None):
        self.op = op
        self.value = value
        self.type = type


class ListLiteralIR(IR):
    def __init__(self, elements, type=None):
        self.elements = elements
        self.type = type


class IdentifierIR(IR):
    def __init__(self, name):
        self.name = name
