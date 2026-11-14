from utils.errors import *


class ScopeAnalyzer:
    def __init__(self, ctx):
        if "stm" not in ctx:
            raise Exception("No stm in context")

        self.stm = ctx["stm"]

    def run_stmt(self, ast, symbol):
        pass

    def run_eval(self, ast, symbol):
        pass
