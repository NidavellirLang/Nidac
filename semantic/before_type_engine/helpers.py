from dataclasses import dataclass
from collections.abc import Mapping
from AST.base import AST


def v_args(parent=False, is_child=False, childs=False):
    def decorator(func):
        func.__parent__ = parent
        func.__is_child__ = is_child
        func.__req_children__ = childs
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

        if isinstance(value, (AST, list)):
            yield name, value

        # elif isinstance(value, (list, tuple)):
        #     for child in value:
        #         if not isinstance(child, AST):
        #             raise TypeError(f"Invalid child in {type(ast).__name__}.{name}")
        #         yield name, child

        else:
            raise TypeError(f"Invalid child field: {type(ast).__name__}.{name}")


@dataclass(slots=True)
class Parent:
    this: AST
    parent: Parent | None


class ChildResults(Mapping):
    __slots__ = ("_data",)

    def __init__(self, data=None):
        self._data = {} if data is None else data

    def __getitem__(self, key):
        return self._data[key]

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __getattr__(self, name):
        try:
            return self._data[name]
        except KeyError:
            raise AttributeError(f"Child result '{name}' does not exist") from None

    def __repr__(self):
        return f"ChildResults({self._data!r})"
