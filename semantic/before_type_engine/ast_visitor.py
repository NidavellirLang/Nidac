from utils.traversal import Parent, Traversal

from .pipeline import DEFAULT_VISITORS


class ASTVisitor(Traversal):
    """Traversal bound to the AST layer's processor set."""

    PROCESSORS = DEFAULT_VISITORS


Visitor = ASTVisitor

__all__ = ["ASTVisitor", "Parent", "Visitor"]
