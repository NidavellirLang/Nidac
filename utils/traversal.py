"""Layer-agnostic tree traversal for compiler processors.

The traversal is shared by every compiler layer (AST, Symbol, HIR, LIR, ...)
and therefore knows nothing about any of them. It only relies on duck-typed
node conventions:

* ``__children__`` - optional tuple of child field names (``str``) or child
  descriptors exposing ``name`` / ``optional``. Nodes without the attribute
  are treated as leaves.
* ``__scope__`` - optional bool marking the node as a scope boundary.

Entry points, counters, AST flags and handlers in the child tuple only work if
their default is ``None``: a scalar is never descended into, so anything that
lives inside a node has to be referenced as a child. List fields may mix nodes
with plain values; the non-node entries are ignored.

Processors are plain classes registered per layer. They expose
``visit_<NodeType>`` methods, may restrict themselves to a node subset with a
``targets`` attribute, and opt into extra arguments through :func:`v_args`.
"""

from collections.abc import Mapping
from dataclasses import dataclass, is_dataclass

from .errors import NidavellirInternalError


__all__ = [
    "Child",
    "ChildResults",
    "Parent",
    "Traversal",
    "iter_children",
    "v_args",
    "vc_args",
]


_MISSING = object()


@dataclass(frozen=True, slots=True)
class Child:
    """Marks a ``__children__`` entry as optional.

    Plain field names are required children; wrapping one in ``Child`` allows
    it to be ``None`` (or absent) without aborting the traversal.
    """

    name: str
    optional: bool = False


def v_args(parent=False, is_child=False, childs=False):
    """Declare the optional arguments handed to a visit method."""

    def decorator(func):
        func.__parent__ = parent
        func.__is_child__ = is_child
        func.__req_children__ = childs
        return func

    return decorator


def vc_args(ctx=False):
    """Declare that a processor wants the compilation context injected."""

    def decorator(classes):
        classes.__req_ctx__ = ctx
        return classes

    return decorator


@dataclass(slots=True)
class Parent:
    this: object
    parent: "Parent | None"


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


def _child_spec(spec):
    if isinstance(spec, str):
        return spec, False

    return spec.name, spec.optional


def is_node(value):
    """Whether a child field value should be traversed as a node.

    Layer agnostic: any object declaring ``__children__`` or built as a
    dataclass counts as a node, everything else is a plain value.
    """

    return hasattr(value, "__children__") or is_dataclass(type(value))


def iter_children(node):
    """Yield ``(field_name, child_or_child_list)`` for a node's children.

    Missing fields are skipped, ``None`` is skipped when the field is declared
    optional and rejected otherwise. Nodes without ``__children__`` simply
    yield nothing.
    """

    for spec in getattr(node, "__children__", ()):
        name, optional = _child_spec(spec)

        value = getattr(node, name, _MISSING)

        if value is _MISSING:
            continue

        if value is None:
            if optional:
                continue
            raise ValueError(f"{type(node).__name__}.{name} cannot be None")

        if isinstance(value, list):
            yield name, [item for item in value if is_node(item)]
            continue

        if is_node(value):
            yield name, value
            continue

        raise TypeError(f"Invalid child field: {type(node).__name__}.{name}")


class Traversal:
    """Walks a node tree and dispatches to the registered processors.

    Result collection is namespace based: processors declaring
    ``__only_namespace__`` contribute under their base class name, which lets
    a processor consume child results produced by another one.
    """

    PROCESSORS = ()
    __slots__ = ("ctx", "processors")

    def __init__(self, ctx=None, processors=None):
        self.ctx = ctx
        self.processors = []

        self.init_processors(
            self.PROCESSORS if processors is None else processors,
        )

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def init_processors(self, processors):
        for processor in processors:
            if getattr(processor, "__req_ctx__", False):
                self.processors.append(processor(ctx=self.ctx))
            else:
                self.processors.append(processor())

    def get_namespace(self, processor):
        if not getattr(processor, "__only_namespace__", False):
            return None

        bases = type(processor).__bases__

        if not bases or bases[0] is object:
            raise NidavellirInternalError(
                f"Namespace base not found for {type(processor).__name__}"
            )

        return bases[0]

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def visit_name(self, node):
        return f"visit_{type(node).__name__}"

    def is_req(self, processor, node):
        targets = getattr(processor, "targets", None)

        if targets is None:
            return True

        return isinstance(node, targets)

    def is_scope(self, node):
        return getattr(node, "__scope__", False)

    def requires_child_response(self, fn):
        return getattr(fn, "__req_children__", False)

    def get_matching_processors(self, node):
        name = self.visit_name(node)
        matching = []

        for processor in self.processors:
            if not self.is_req(processor, node):
                continue

            specific = getattr(processor, name, None)
            generic = getattr(processor, "visit", None)

            if specific is None and generic is None:
                raise NidavellirInternalError(
                    f"Visitor {type(processor).__name__} does not handle "
                    f"{type(node).__name__}"
                )

            matching.append((processor, specific, generic))

        return matching

    def func_caller(self, fn, parent, is_child, children_response, *args):
        func = getattr(fn, "__func__", fn)
        kw = {}

        if getattr(func, "__parent__", False):
            kw["parent"] = parent

        if getattr(func, "__is_child__", False):
            kw["is_child"] = is_child

        if getattr(func, "__req_children__", False):
            kw["childs"] = children_response

        return fn(*args, **kw)

    # ------------------------------------------------------------------
    # Child result handling
    # ------------------------------------------------------------------

    def process_children(self, node, parent, required_namespaces):
        child_results = {}

        for name, child in iter_children(node):
            if isinstance(child, list):
                result = [
                    self.visit(item, parent, True, required_namespaces)
                    for item in child
                ]
            else:
                result = self.visit(child, parent, True, required_namespaces)

            child_results[name] = result

        return child_results

    def calculate_children(self, namespace, children_response):
        final = {}

        for child_name, child_response in children_response.items():
            if isinstance(child_response, list):
                response = []

                for item in child_response:
                    value = item.get(namespace)

                    if value is None:
                        raise NidavellirInternalError(
                            f"Child result required for '{child_name}'"
                        )

                    response.append(value)

                final[child_name] = response
                continue

            value = child_response.get(namespace)

            if value is None:
                raise NidavellirInternalError(
                    f"Child result required for '{child_name}'"
                )

            final[child_name] = value

        return ChildResults(final)

    # ------------------------------------------------------------------
    # Core walk
    # ------------------------------------------------------------------

    def visit(self, node, parent=None, is_child=False, required_namespaces=None):
        current = Parent(node, parent)

        scoped = self.is_scope(node)

        if scoped:
            self.on_enter_scope(node)

        try:
            matching = self.get_matching_processors(node)

            requested = set()

            for processor, specific, generic in matching:
                requires_response = (
                    self.requires_child_response(specific)
                    if specific is not None
                    else False
                ) or (
                    self.requires_child_response(generic)
                    if generic is not None
                    else False
                )

                if not requires_response:
                    continue

                namespace = self.get_namespace(processor)

                if namespace is None:
                    raise NidavellirInternalError(
                        f"{type(processor).__name__} requires child results "
                        "but does not define a namespace"
                    )

                requested.add(namespace)

            if required_namespaces is not None:
                requested.intersection_update(required_namespaces)

            child_results = self.process_children(node, current, requested)
            child_results = ChildResults(child_results)

            result = {}

            for processor, specific, generic in matching:
                namespace = self.get_namespace(processor)

                if (
                    required_namespaces is not None
                    and namespace not in required_namespaces
                ):
                    collect_result = False
                else:
                    collect_result = namespace is not None

                specific_res = None

                specific_requires = (
                    self.requires_child_response(specific)
                    if specific is not None
                    else False
                )

                generic_requires = (
                    self.requires_child_response(generic)
                    if generic is not None
                    else False
                )

                if specific is not None:
                    specific_children = None

                    if specific_requires:
                        specific_children = self.calculate_children(
                            namespace,
                            child_results,
                        )

                    specific_res = self.func_caller(
                        specific, parent, is_child, specific_children, node
                    )

                if generic is not None:
                    generic_children = None

                    if generic_requires:
                        generic_children = self.calculate_children(
                            namespace,
                            child_results,
                        )

                    generic_result = self.func_caller(
                        generic, parent, is_child, generic_children, node
                    )

                    if specific is None:
                        specific_res = generic_result

                if collect_result:
                    result[namespace] = specific_res

            return result

        finally:
            if scoped:
                self.on_exit_scope(node)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def call_processor_fn(self, name, *args):
        for processor in self.processors:
            fn = getattr(processor, name, None)

            if fn is not None:
                fn(*args)

    def on_exit_scope(self, node):
        self.call_processor_fn("on_exit_scope", node)

    def on_enter_scope(self, node):
        self.call_processor_fn("on_enter_scope", node)

    def on_start(self):
        self.call_processor_fn("on_start")

    def on_end(self):
        self.call_processor_fn("on_end")

    def run(self, nodes):
        self.on_start()

        try:
            for node in nodes:
                self.visit(node)
        finally:
            self.on_end()
