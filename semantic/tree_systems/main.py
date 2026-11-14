from .tree_builder import SymbolTreeBuilder
from utils import SysArgs
from nida_ast.base import *


def semantic_analyze(ast_tree, ctx):
    stb = SymbolTreeBuilder(ast_tree, ctx)
    stb.run()

    if SysArgs.dump_sym_tree:
        print("===== Symbol Tree =====")
        print(stb.st)

    return stb
