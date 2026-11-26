from .pipeline import DEFAULT_VISITORS
from .helpers import Parent, children


class Visitor:
    def __init__(self, ctx):
        self.ctx = ctx
        self.visitors = []

        self.init_visitors()

    def init_visitors(self):
        for visitor in DEFAULT_VISITORS:
            if hasattr(visitor, "__req_ctx__") and visitor.__req_ctx__:
                self.visitors.append(visitor(ctx=self.ctx))
            else:
                self.visitors.append(visitor())

    def func_caller(self, fn, parent, is_child, *a):
        func = getattr(fn, "__func__", fn)
        kw = {}

        if getattr(func, "__parent__", False):
            kw["parent"] = parent

        if getattr(func, "__is_child__", False):
            kw["is_child"] = is_child

        return fn(*a, **kw)

    def is_req(self, visitor, ast):
        if hasattr(visitor, "targets"):
            targets = visitor.targets
            if isinstance(ast, targets):
                return True

            return False

        return True

    def visit(self, ast, parent=None, is_child=False):
        current = Parent(ast, parent)

        for c in children(ast):
            self.visit(c, current, True)

        for vs in self.visitors:
            name = f"visit_{type(ast).__name__}"
            if not self.is_req(vs, ast):
                continue

            fn = None

            if hasattr(vs, name):
                fn = getattr(vs, name)
            elif hasattr(vs, "visit"):
                fn = getattr(vs, "visit")
            else:
                raise Exception(
                    f"Visitor {vs} does not have method {type(ast).__name__}"
                )

            self.func_caller(fn, parent, is_child, ast)

    def run(self, ast_tree):
        for ast in ast_tree:
            self.visit(ast)
