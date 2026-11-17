from type_systems.types import IntType

from ..transformer import IRTransform, PassContractError
from ...irs import (
    BlockIR,
    ClassIR,
    DefinitionIR,
    FunctionIR,
    IRImport,
    NumberIR,
    ReturnIR,
    StructIR,
)


class CollectMain(IRTransform):
    module_types = (ClassIR, DefinitionIR, FunctionIR, IRImport, StructIR)

    def run(self, module):
        if not isinstance(module, BlockIR):
            raise PassContractError(
                f"{type(self).__name__} expects BlockIR, got {type(module).__name__}"
            )

        module_stmts = []
        main_stmts = []

        for stmt in module.body:
            target = module_stmts if isinstance(stmt, self.module_types) else main_stmts
            target.append(stmt)

        int_type = IntType(byte_size=4, signed=True)
        main_stmts.append(
            ReturnIR(
                value=NumberIR(value=0, type=int_type),
                type=int_type,
            )
        )
        module_stmts.append(
            FunctionIR(
                name="main",
                args=[],
                body=main_stmts,
                type=int_type,
                is_main_func=True,
            )
        )

        module.body = module_stmts
        self.changed = True
        return module
