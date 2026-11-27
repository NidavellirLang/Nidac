from utils.errors import NidavellirTypeError
from ...helpers import vc_args


@vc_args(ctx=True)
class BaseBuilder:
    __slots__ = ("symbol_table", "id_alloc", "ctx")

    def __init__(self, ctx):
        self.ctx = ctx
        self.id_alloc = None
        self.symbol_table = None
        self.symbol_tree = []

    def on_start(self):
        self.id_alloc = self.ctx["id_alloc"]
        self.symbol_table = self.ctx["symbol_table"]

    def get_id(self, ast):
        node_id = ast.node_id

        if node_id is None:
            raise NidavellirTypeError("Node id not found", ast.line)

        return node_id

    def create(self, symbol, ast, register=True, **kw):
        result = symbol(ast_node=ast, **kw)

        if register:
            self.symbol_table.define_symbol_id(self.get_id(ast), result)

        return result
