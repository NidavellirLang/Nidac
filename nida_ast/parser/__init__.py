from .grammar_manager import GrammarManager
from utils import SysArgs

if SysArgs.grammar:
    GrammarManager().process_grammar()

from .parser import Parser

__all__ = ["Parser"]
