from .manager import PassManager
from .transforms import CollectMain, IntrinsicTransform

DEFAULT_PASSES = (
    CollectMain,
    IntrinsicTransform,
)


def build_default():
    return PassManager(*(pass_type() for pass_type in DEFAULT_PASSES))
