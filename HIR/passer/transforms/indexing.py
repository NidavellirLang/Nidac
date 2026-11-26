from ..transformer import IRTransform
from ...irs import *
from utils.errors import NidavellirNotImplementedError
from type_systems.types import StringType


class IndexPasser(IRTransform):
    targets = (IndexAccessIR,)

    def visit(self, node: IndexAccessIR):
        target = node.target
        index = node.index

        if isinstance(target.type, StringType):
            return CallIR(
                target=IdentifierIR(name="Nida_str_index"),
                args=[target, index],
                type=StringType(),
            )
        else:
            raise NidavellirNotImplementedError(
                f"Indexing not implemented for type {target.type}"
            )
