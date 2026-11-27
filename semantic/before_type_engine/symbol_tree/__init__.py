from .builder import SymbolTreeBuilder
from .builders.expressions import ExpressionBuilder
from .builders.statements import StatementBuilder


def get_symbol_visitors():
    return (
        StatementBuilder,
        ExpressionBuilder,
        SymbolTreeBuilder,
    )
