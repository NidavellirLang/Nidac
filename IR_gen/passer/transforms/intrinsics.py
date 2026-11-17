from ..transformer import IRTransform
from ...irs import *
from utils import SysArgs


class IntrinsicTransform(IRTransform):
    def intrinsic_print(self, Hir):
        if SysArgs.no_print:
            return []

        SysArgs.add_extra_c_include("print.h")

        args = Hir.args
        chunks = [args[i : i + 4] for i in range(0, len(args), 4)]

        body = []

        for i, chunk in enumerate(chunks):
            is_last = i == len(chunks) - 1

            call_args = [
                *chunk,
                BooleanIR(value=is_last),
            ]

            target = IdentifierIR(name=f"_Nida_print_a{len(chunk)}")

            call = CallIR(
                target=target,
                args=call_args,
                type=NoneType(),
            )

            body.append(StmtExprIR(expr=call))

        return BlockIR(body=body)

    def visit(self, node):
        if isinstance(node, IntrinsicCallIR) and isinstance(node.target, IdentifierIR):
            method = getattr(self, f"intrinsic_{node.target.name}", None)
            if method is not None:
                return method(node)
        return node
