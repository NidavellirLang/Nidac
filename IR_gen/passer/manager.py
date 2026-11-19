from ..irs import IR


class PassManager:
    def __init__(self, *passes):
        self.passes = passes

    def run(self, node: IR, ctx=None) -> IR:
        for transform in self.passes:
            node = transform.run(node, ctx)
        return node
