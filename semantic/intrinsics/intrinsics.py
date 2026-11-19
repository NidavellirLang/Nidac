from nida_ast.base import *
from .intrinsic_types import *

INTRINSICS = {
    "print": IntrinsicAST(
        name="print",
        type=NoneType(),
        params=ParamsType(AnyType(), is_variadic=True),
    ),
    "range": IntrinsicAST(
        name="range",
        type=NoneType(),
        params=ParamsType(OneOf(IntType), min_t=1, max_t=3),
    ),
    "input": IntrinsicAST(
        name="input",
        type=StringType(),
        params=ParamsType(OneOf(StringType), args_count=1),
    ),
}
