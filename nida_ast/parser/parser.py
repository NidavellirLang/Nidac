from pathlib import Path
from utils import SysArgs
from .transformer import ASTTranslator

from .lark_loader import LarkLoader


class NidaIndenter(LarkLoader.Indenter):
    NL_type = "_NEWLINE"
    OPEN_PAREN_types = ["LPAR"]
    CLOSE_PAREN_types = ["RPAR"]
    INDENT_type = "_INDENT"
    DEDENT_type = "_DEDENT"
    tab_len = 4


class Parser:

    def __init__(self, source_code, ctx):
        if not source_code:
            raise ValueError("Source code cannot be empty")

        self.grammar_path = SysArgs.grammar_path

        self.source_code = source_code
        self.ctx = ctx
        self.id_alloc = ctx["id_alloc"]

        self.ast_tree = None
        self.parser = None

    def error(self, error):
        raise error

    def parse_dynamic(self):
        self.parser = LarkLoader.Lark.open(
            str(self.grammar_path),
            parser="lalr",
            lexer="basic",
            start="start",
            propagate_positions=True,
            postlex=NidaIndenter(),
            maybe_placeholders=False,
            transformer=ASTTranslator(
                visit_tokens=True, id_alloc=self.id_alloc, source=self.source_code
            ),
        )
        try:
            self.ast_tree = self.parser.parse(self.source_code)
        except Exception as e:
            self.error(e)

        return self.ast_tree

    def parse_standalone(self):
        self.parser = LarkLoader.Lark_StandAlone()

        translator = ASTTranslator(
            visit_tokens=True,
            id_alloc=self.id_alloc,
            source=self.source_code,
        )

        try:
            # self.ast_tree = translator.transform(self.parser.parse(self.source_code))
            pass
        except Exception as e:
            self.error(e)

        return self.ast_tree

    def run(self):
        is_standalone = LarkLoader.is_standalone
        if is_standalone:
            return self.parse_standalone()
        else:
            return self.parse_dynamic()
