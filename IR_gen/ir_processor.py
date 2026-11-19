from .ir_gen import IRGen
from .irs import BlockIR
from .passer import PassManager, build_default


class IRProcessor:
    def __init__(self, ast_tree, ctx, passes=None):
        self.ctx = ctx
        self.generator = IRGen(ast_tree, ctx)
        self.passes = passes
        self.hirs = None
        self.final_irs = None

    def generate_irs(self):
        self.hirs = self.generator.run()
        return self.hirs

    def run_passer(self):
        if self.hirs is None:
            raise ValueError("IR generation must run before passes")

        manager = build_default() if self.passes is None else PassManager(*self.passes)
        root = manager.run(BlockIR(body=self.hirs), self.ctx)

        self.final_irs = root.body if isinstance(root, BlockIR) else [root]
        return self.final_irs

    def run(self):
        self.generate_irs()
        self.run_passer()

        if self.final_irs is None:
            raise ValueError("IR pipeline produced no output")

        return self.final_irs
