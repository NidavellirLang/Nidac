from dataclasses import dataclass
from .lirs import *


@dataclass(frozen=True)
class LIRRule:
    instruction: type | None = None
    result_type: str | None = None


INT_OPS = {
    "+": LIRRule(instruction=AddLIR),
    "-": LIRRule(instruction=SubLIR),
    "*": LIRRule(instruction=MulLIR),
    "/": LIRRule(instruction=DivLIR),
    "%": LIRRule(instruction=ModLIR),
    "==": LIRRule(instruction=EqLIR, result_type="bool"),
    "!=": LIRRule(instruction=NeLIR, result_type="bool"),
    ">": LIRRule(instruction=GtLIR, result_type="bool"),
    "<": LIRRule(instruction=LtLIR, result_type="bool"),
    ">=": LIRRule(instruction=GeLIR, result_type="bool"),
    "<=": LIRRule(instruction=LeLIR, result_type="bool"),
    "or": LIRRule(instruction=OrLIR, result_type="bool"),
    "and": LIRRule(instruction=AndLIR, result_type="bool"),
}

# STR_OPS = {
#     "+": LIRRule(runtime="Nida_str_concat"),
#     "==": LIRRule(runtime="Nida_str_eq", result_type="bool"),
#     "!=": LIRRule(runtime="Nida_str_ne", result_type="bool"),
# }
