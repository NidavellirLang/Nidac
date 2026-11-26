from dataclasses import dataclass
from AST.base import AST
from .pipeline import DEFAULT_VISITORS


def v_args(parent=False, is_child=False):
    def decorator(func):
        func.__parent__ = parent
        func.__is_child__ = is_child
        return func

    return decorator


def vc_args(ctx=False):
    def decorator(classes):
        classes.__req_ctx__ = ctx
        return classes

    return decorator


def children(ast):
    for spec in ast.__children__:
        if isinstance(spec, str):
            name = spec
            optional = False
        else:
            name = spec.name
            optional = spec.optional

        value = getattr(ast, name)

        if value is None:
            if optional:
                continue
            raise ValueError(f"{type(ast).__name__}.{name} cannot be None")

        if isinstance(value, AST):
            yield value
        elif isinstance(value, (list, tuple)):
            for child in value:
                if not isinstance(child, AST):
                    raise TypeError(f"Invalid child in {type(ast).__name__}.{name}")
                yield child
        else:
            raise TypeError(f"Invalid child field: {type(ast).__name__}.{name}")


@dataclass(slots=True)
class Parent:
    this: AST
    parent: Parent | None
