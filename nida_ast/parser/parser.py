from lark import Lark
from lark.indenter import Indenter

from pathlib import Path

from .transformer import ASTTranslator


class NidaIndenter(Indenter):
    NL_type = "_NEWLINE"
    OPEN_PAREN_types = ["LPAR"]
    CLOSE_PAREN_types = ["RPAR"]
    INDENT_type = "_INDENT"
    DEDENT_type = "_DEDENT"
    tab_len = 4


class Parser:
    grammar_path = Path(__file__).parent / "grammar.lark"

    def __init__(self, source_code, ctx):
        if not source_code:
            raise

        self.source_code = source_code
        self.ctx = ctx
        self.id_alloc = ctx["id_alloc"]

        self.ast_tree = []
        self.parser = None

        self.run()

    def error(self, error):
        raise error

    def run(self):
        self.parser = Lark.open(
            str(self.grammar_path),
            parser="lalr",
            lexer="basic",
            start="start",
            propagate_positions=True,
            postlex=NidaIndenter(),
            # transformer=ASTTranslator(
            #     visit_tokens=True, id_alloc=self.id_alloc, source=self.source_code
            # ),
        )
        try:
            self.ast_tree = self.parser.parse(self.source_code)
        except Exception as e:
            self.error(e)

        return self.ast_tree
