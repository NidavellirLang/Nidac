from ..transformer import IRTransform
from ...irs import *
from utils.errors import *
from utils import SysArgs


class IntrinsicTransform(IRTransform):
    targets = (IntrinsicCallIR,)

    def intrinsic_print(self, Hir):
        if SysArgs.no_print:
            return BlockIR(body=[])

        self.ctx.add_c_header("<print.h>")

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

    def intrinsic_ord(self, hir):
        return CallIR(
            target=IdentifierIR(name="Nida_str_ord0"),
            args=[hir.args[0]],
            type=IntType(byte_size=8),
        )

    def intrinsic_len(self, hir):
        return CallIR(
            target=IdentifierIR(name="Nida_str_len"),
            args=[hir.args[0]],
            type=IntType(byte_size=8),
        )

    def intrinsic_input(self, hir):
        self.ctx.add_c_header("<input.h>")
        return CallIR(
            target=IdentifierIR(name="Nida_input"),
            args=[hir.args[0]],
            type=StringType(),
        )

    def visit(self, node):
        if isinstance(node, IntrinsicCallIR) and isinstance(node.target, IdentifierIR):
            method = getattr(self, f"intrinsic_{node.target.name}", None)
            if method is not None:
                return method(node)
            else:
                raise NidavellirInternalError(f"Unknown intrinsic: {node.target.name}")
        return node
