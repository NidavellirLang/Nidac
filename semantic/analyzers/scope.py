from utils.errors import *
from nida_ast.base import *


class ScopeAnalyzer:
    def __init__(self, ctx):
        if "stm" not in ctx:
            raise Exception("No stm in context")

        self.stm = ctx["stm"]

    # TODO: impl
    # def stmt_ReturnAST(self, ast, sym):
    #     # raise Exception(sym.value.lookup)

    #     if not isinstance(ast.value, VariableAST):
    #         return

    #     value = sym.value
    #     main = value.lookup

    #     if main is None:
    #         return

    #     self.stm.mark_escaping(main.node_id)
    #     # breakpoint()

    def run_stmt(self, ast, symbol):
        method_name = f"stmt_{type(ast).__name__}"
        visitor = getattr(self, method_name, None)
        if visitor is None:
            return

        visitor(ast, sym=symbol)

    def run_eval(self, ast, symbol):
        method_name = f"eval_{type(ast).__name__}"
        visitor = getattr(self, method_name, None)
        if visitor is None:
            return

        visitor(ast, sym=symbol)
