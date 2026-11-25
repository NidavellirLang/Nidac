from utils import SysArgs

if SysArgs.grammar:
    from .grammar_manager import GrammarManager

    GrammarManager().process_grammar()

from .parser import Parser

__all__ = ["Parser"]
