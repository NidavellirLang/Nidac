from type_systems.types import resolve_type, StringType, NoneType, ClassType


class Symbol:
    def _format(self, indent=0, seen=None):
        if seen is None:
            seen = set()

        prefix = "  " * indent
        class_name = self.__class__.__name__

        if id(self) in seen:
            return f"{prefix}{class_name}(...)"

        seen.add(id(self))

        attrs = {
            k: v
            for k, v in self.__dict__.items()
            if not k.startswith("_") and k != "ast_node"
        }

        if not attrs:
            return f"{prefix}{class_name}()"

        lines = [f"{prefix}{class_name}:"]

        for key, value in attrs.items():
            field_prefix = f"{prefix}  {key}:"

            if isinstance(value, Symbol):
                lines.append(field_prefix)
                lines.append(value._format(indent + 2, seen))

            elif isinstance(value, list):
                if not value:
                    lines.append(f"{field_prefix} []")
                    continue

                lines.append(field_prefix)

                for item in value:
                    if isinstance(item, Symbol):
                        lines.append(f"{prefix}    -")
                        lines.append(item._format(indent + 3, seen))
                    else:
                        lines.append(f"{prefix}    - {self._format_value(item)}")

            elif isinstance(value, dict):
                if not value:
                    lines.append(f"{field_prefix} {{}}")
                    continue

                lines.append(field_prefix)

                for k, v in value.items():
                    if isinstance(v, Symbol):
                        lines.append(f"{prefix}    {k}:")
                        lines.append(v._format(indent + 3, seen))
                    else:
                        lines.append(f"{prefix}    {k}: {self._format_value(v)}")

            else:
                lines.append(f"{field_prefix} {self._format_value(value)}")

        seen.remove(id(self))
        return "\n".join(lines)

    @staticmethod
    def _format_value(value):
        if isinstance(value, Symbol):
            return f"<{type(value).__name__}>"

        if isinstance(value, list):
            return repr(value)

        if isinstance(value, dict):
            return repr(value)

        if hasattr(value, "__class__") and (value.__class__.__name__.endswith("Type")):
            return repr(value)

        return repr(value)

    def __repr__(self):
        return self._format()


class AssignSymbol(Symbol):
    def __init__(self, name, type, value, ast_node, re_assign=None):
        self.name = name
        self.type = resolve_type(type)
        self.value = value

        self.ast_node = ast_node

        self.parent_assign = None

        self.uses = []

        self.field = None
        self.base_sym = None

        self.is_re_assign = re_assign

    def set_type_to_AST(self):
        self.ast_node.type = self.type
        if self.parent_assign is not None and not self.chain:
            self.parent_assign.type = self.type
            self.parent_assign.set_type_to_AST()


class DefinitionSymbol(Symbol):
    def __init__(self, name, type, value, ast_node):
        self.name = name
        self.type = resolve_type(type)
        self.value = value
        self.ast_node = ast_node

        self.parent_assign = None

        self.uses = []

    def set_type_to_AST(self):
        self.ast_node.type = self.type


class NumberSymbol(Symbol):
    def __init__(self, value, ast_node):
        self.value = value
        self.ast_node = ast_node

        self.type = None

    def set_type_to_AST(self):
        self.ast_node.type = self.type


class StringSymbol(Symbol):
    def __init__(self, value, ast_node):
        self.value = value
        self.ast_node = ast_node

        self.type = StringType()

    def set_type_to_AST(self):
        self.ast_node.type = self.type


class NoneSymbol(Symbol):
    def __init__(self, ast_node):
        self.ast_node = ast_node

        self.type = NoneType()

    def set_type_to_AST(self):
        self.ast_node.type = self.type


class FunctionSymbol(Symbol):
    def __init__(self, name, type, args, ast_node, is_variadic=False):
        self.name = name
        self.type = resolve_type(type)
        self.args = args
        self.ast_node = ast_node
        self.is_variadic = is_variadic

        self.body = []

        self.uses = []
        self.returned = []

        self.is_called = False

    def set_type_to_AST(self):
        self.ast_node.type = self.type


class ReturnSymbol(Symbol):
    def __init__(self, value, ast_node):
        self.value = value
        self.ast_node = ast_node


class CallSymbol(Symbol):
    def __init__(self, name, args, lookup, ast_node):
        self.name = name
        self.args = args
        self.lookup = lookup
        self.ast_node = ast_node

        self.receiver_chain = []

        self.arg_offset = 0

        self.type = None

    def set_type_to_AST(self):
        self.ast_node.type = self.type


class IntrinsicCallSymbol(Symbol):
    def __init__(self, intrinsic, name, args, ast_node):
        self.intrinsic = intrinsic
        self.name = name
        self.args = args
        self.ast_node = ast_node

        self.type = None


class VariableSymbol(Symbol):
    def __init__(self, name, lookup, ast_node):
        self.name = name
        self.lookup = lookup
        self.ast_node = ast_node

        self.type = None

    def set_type_to_AST(self):
        self.ast_node.type = self.type


class BinaryOpSymbol(Symbol):
    def __init__(self, op, left_sym, right_sym, ast_node=None):
        self.op = op
        self.left_sym = left_sym
        self.right_sym = right_sym
        self.ast_node = ast_node

        self.type = None

        self.max_val = None
        self.min_val = None

    def set_type_to_AST(self):
        self.ast_node.type = self.type


class UnaryOpSymbol(Symbol):
    def __init__(self, op, right_sym, ast_node=None):
        self.op = op
        self.right_sym = right_sym
        self.ast_node = ast_node

        self.type = None

    def set_type_to_AST(self):
        self.ast_node.type = self.type


class ForSymbol(Symbol):
    def __init__(self, target, source, body, loop_count, ast_node):
        self.target = target
        self.source = source
        self.ast_node = ast_node
        self.body = body
        self.loop_count = loop_count

        self.type = None


class UnavailableSymbol(Symbol):
    def __init__(self, why, ast_node):
        self.why = why
        self.ast_node = ast_node


class IfSymbol(Symbol):
    def __init__(
        self,
        cond,
        body,
        elifs,
        else_body,
        ast_node,
        body_scope,
        else_scope=None,
        merges=None,
    ):
        self.cond = cond
        self.body = body
        self.body_scope = body_scope

        self.elifs = elifs
        self.else_body = else_body
        self.else_scope = else_scope

        self.ast_node = ast_node

        self.merges = merges


class ElifSymbol(Symbol):
    def __init__(self, cond, body, ast_node, scope):
        self.cond = cond
        self.body = body
        self.scope = scope
        self.ast_node = ast_node


class WhileSymbol(Symbol):
    def __init__(self, cond, body, ast_node):
        self.cond = cond
        self.body = body
        self.ast_node = ast_node


class BooleanSymbol(Symbol):
    def __init__(self, value, ast_node):
        self.value = value
        self.ast_node = ast_node
        self.type = None


class ClassSymbol(Symbol):
    def __init__(self, name, ast_node):
        self.name = name
        self.ast_node = ast_node

        self.body = []

        self.init_fn = None
        self.params = None

        self.fields = {}
        self.field_syms = {}
        self.methods = {}

        self.method_syms = {}

        self.uses = []

        self.type = ClassType(name)

    def set_type_to_AST(self):
        self.ast_node.type = self.type


class FieldAccessSymbol(Symbol):
    def __init__(self, target, chain, ast_node):
        self.target = target
        self.chain = chain
        self.ast_node = ast_node

        self.type = None

    def set_type_to_AST(self):
        self.ast_node.type = self.type


class SelfSymbol(Symbol):
    def __init__(self, ast_node, class_name=None):
        self.ast_node = ast_node
        self.class_name = class_name

        self.type = None

    def set_type_to_AST(self):
        if hasattr(self.ast_node, "chain"):
            return

        self.ast_node.type = self.type


class ConstructorCallSymbol(Symbol):
    def __init__(self, name, args, lookup, ast_node):
        self.name = name
        self.args = args
        self.lookup = lookup
        self.ast_node = ast_node

        self.arg_offset = 1

        self.type = None

    def set_type_to_AST(self):
        self.ast_node.type = self.type


class ListLiteralSymbol(Symbol):
    def __init__(self, elements, ast_node):
        self.elements = elements
        self.appended_elements = []
        self.ast_node = ast_node

        self.type = None

    def set_type_to_AST(self):
        self.ast_node.type = self.type


class MergeAssignmentSymbol(Symbol):
    def __init__(self, assign_sym, ast_node, norm_debug_name=None):
        self.merge_assign_sym = assign_sym
        self.ast_node = ast_node

        self.norm_debug_name = norm_debug_name


class IdentifierSymbol(Symbol):
    def __init__(self, name, ast_node):
        self.name = name
        self.ast_node = ast_node
        self.lookup = None
        self.field_name = None
        self.type = None

    def set_type_to_AST(self):
        self.ast_node.type = self.type
