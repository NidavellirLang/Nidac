from .pipeline import DEFAULT_VISITORS
from .helpers import Parent, children, ChildResults
from utils.errors import *


class Visitor:
    def __init__(self, ctx):
        self.ctx = ctx
        self.visitors = []

        self.init_visitors()

    def init_visitors(self):
        for visitor in DEFAULT_VISITORS:
            if getattr(visitor, "__req_ctx__", False):
                self.visitors.append(visitor(ctx=self.ctx))
            else:
                self.visitors.append(visitor())

    def get_namespace(self, visitor):
        if not getattr(visitor, "__only_namespace__", False):
            return None

        bases = type(visitor).__bases__

        if not bases or bases[0] is object:
            raise NidavellirInternalError(
                f"Namespace base not found for {type(visitor).__name__}"
            )

        return bases[0]

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

    def is_req(self, visitor, ast):
        targets = getattr(visitor, "targets", None)

        if targets is None:
            return True

        return isinstance(ast, targets)

    def is_req_scope(self, ast):
        return getattr(ast, "__scope__", False)

    def requires_child_response(self, fn):
        return getattr(fn, "__req_children__", False)

    def get_matching_visitors(self, ast):
        name = f"visit_{type(ast).__name__}"
        matching = []

        for vs in self.visitors:
            if not self.is_req(vs, ast):
                continue

            specific = getattr(vs, name, None)
            generic = getattr(vs, "visit", None)

            if specific is None and generic is None:
                raise NidavellirInternalError(
                    f"Visitor {type(vs).__name__} does not handle "
                    f"{type(ast).__name__}"
                )

            matching.append((vs, specific, generic))

        return matching

    def process_childrens(self, ast, parent, required_namespaces):
        child_results = {}

        for name, child in children(ast):
            if isinstance(child, list):
                result = [
                    self.visit(
                        item,
                        parent,
                        True,
                        required_namespaces,
                    )
                    for item in child
                ]
            else:
                result = self.visit(
                    child,
                    parent,
                    True,
                    required_namespaces,
                )

            child_results[name] = result

        return child_results

    def calculate_childrens(self, namespace, children_response):
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

    def visit(self, ast, parent=None, is_child=False, required_namespaces=None):
        current = Parent(ast, parent)

        scoped = self.is_req_scope(ast)

        if scoped:
            self.on_enter_scope(ast)

        try:
            matching = self.get_matching_visitors(ast)

            requested = set()

            for vs, specific, generic in matching:
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

                namespace = self.get_namespace(vs)

                if namespace is None:
                    raise NidavellirInternalError(
                        f"{type(vs).__name__} requires child results "
                        "but does not define a namespace"
                    )

                requested.add(namespace)

            if required_namespaces is not None:
                requested.intersection_update(required_namespaces)

            child_results = self.process_childrens(ast, current, requested)
            child_results = ChildResults(child_results)

            result = {}

            for vs, specific, generic in matching:
                namespace = self.get_namespace(vs)

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
                        specific_children = self.calculate_childrens(
                            namespace,
                            child_results,
                        )

                    specific_res = self.func_caller(
                        specific, parent, is_child, specific_children, ast
                    )

                if generic is not None:
                    generic_children = None

                    if generic_requires:
                        generic_children = self.calculate_childrens(
                            namespace,
                            child_results,
                        )

                    generic_result = self.func_caller(
                        generic, parent, is_child, generic_children, ast
                    )

                    if specific is None:
                        specific_res = generic_result

                if collect_result:
                    result[namespace] = specific_res

            return result

        finally:
            if scoped:
                self.on_exit_scope(ast)

    def call_vs_fn(self, name, *args):
        for vs in self.visitors:
            fn = getattr(vs, name, None)

            if fn is not None:
                fn(*args)

    def on_exit_scope(self, ast):
        self.call_vs_fn("on_exit_scope", ast)

    def on_enter_scope(self, ast):
        self.call_vs_fn("on_enter_scope", ast)

    def on_start(self):
        self.call_vs_fn("on_start")

    def on_end(self):
        self.call_vs_fn("on_end")

    def run(self, ast_tree):
        self.on_start()

        try:
            for ast in ast_tree:
                self.visit(ast)
        finally:
            self.on_end()
