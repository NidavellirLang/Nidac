from utils import SysArgs
from IR_gen.irs import *
from type_systems.types import *


def range_intrinsic(Hir):
    args = Hir.args
    arg_c = len(args)

    start = None
    end = None
    step = None

    num_type = args[0].type if args else None

    if arg_c == 1:
        start = NumberIR(value=0, type=num_type)
        end = args[0]
        step = NumberIR(value=1, type=num_type)
    elif arg_c == 2:
        start = args[0]
        end = args[1]
        step = NumberIR(value=1, type=num_type)
    elif arg_c == 3:
        start = args[0]
        end = args[1]
        step = args[2]
    else:
        raise Exception("Range intrinsic takes 1, 2 or 3 arguments")

    return RangeIR(start, end, step)


def input_intrinsic(Hir):
    SysArgs.add_extra_c_include("input.h")
    return CallIR("Nida_input", Hir.args)
