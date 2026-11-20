from ..transformer import IRTransform
from ...irs import *
from utils.errors import *
from type_systems.types import *


# STR_OPS = {
#     "+": LIRRule(runtime="Nida_str_concat"),
#     "==": LIRRule(runtime="Nida_str_eq", result_type="bool"),
#     "!=": LIRRule(runtime="Nida_str_ne", result_type="bool"),
# }
class BinaryOpPasser(IRTransform):
    targets = (BinaryOpIR, UnaryOpIR)

    def visit_binaryop(self, node):
        match node.op:
            case "or" | "and":
                return node

            case "+":
                if isinstance(node.left.type, StringType) and isinstance(
                    node.right.type, StringType
                ):
                    return CallIR(
                        target=IdentifierIR(name="Nida_str_concat"),
                        args=[node.left, node.right],
                        type=StringType(),
                    )

            case "==" | "!=":
                if isinstance(node.left.type, StringType) and isinstance(
                    node.right.type, StringType
                ):
                    call = CallIR(
                        target=IdentifierIR(name="Nida_str_eq"),
                        args=[node.left, node.right],
                        type=BoolType(),
                    )

                    if node.op == "!=":
                        return UnaryOpIR(
                            op="not",
                            value=call,
                            type=BoolType(),
                        )

                    return call

        return node

    def visit_UnaryOpIR(self, node: UnaryOpIR):
        if not isinstance(node.value.type, StringType):
            return node

        match node.op:
            case "not":
                return CallIR(
                    target=IdentifierIR(name="Nida_str_not"),
                    args=[node.value],
                    type=BoolType(),
                )

            case _:
                raise ValueError(f"Unsupported string unary operator: {node.op}")

    def visit(self, node):
        if isinstance(node, BinaryOpIR):
            return self.visit_binaryop(node)

        if isinstance(node, UnaryOpIR):
            return self.visit_UnaryOpIR(node)

        return node
