from .manager import PassManager
from .transforms import *

DEFAULT_PASSES = (
    ClassLowering,
    BoundMethods,
    IntrinsicTransform,
    IndexPasser,
    CollectMain,
)


def build_default():
    return PassManager(*(pass_type() for pass_type in DEFAULT_PASSES))
