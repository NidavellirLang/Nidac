from .checks import get_checks
from .analyzers import get_analyzers
from .symbol_tree import get_symbol_visitors

DEFAULT_VISITORS = (*get_symbol_visitors(), *get_analyzers(), *get_checks())
