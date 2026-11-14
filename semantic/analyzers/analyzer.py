from .scope import ScopeAnalyzer


class Analyzer:
    def __init__(self, ctx):
        self.analyzers = [ScopeAnalyzer(ctx)]

    def run_stmt(self, ast, symbol):
        for analyzer in self.analyzers:
            analyzer.run_stmt(ast, symbol)

    def run_eval(self, ast, symbol):
        for analyzer in self.analyzers:
            analyzer.run_eval(ast, symbol)
