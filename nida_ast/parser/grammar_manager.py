from utils import SysArgs
from utils.errors import NidavellirFileNotFoundError, NidavellirInternalError
from pathlib import Path
import os, sys

try:
    from lark import Lark
    from lark.tools.standalone import gen_standalone
except ImportError:
    raise NidavellirInternalError("Lark is not installed. Please install lark.")


class GrammarManager:
    standalone_path = Path(__file__).parent / "standalone_parser.py"

    def __init__(self):
        self.grammar_path = SysArgs.grammar_path

    def remove_standalone(self):
        if not self.standalone_path.exists():
            raise NidavellirFileNotFoundError(
                f"Standalone parser file not found at {self.standalone_path}"
            )

        try:
            self.standalone_path.unlink()
        except OSError as exc:
            raise NidavellirInternalError(
                f"Standalone parser file could not be removed at {self.standalone_path}: {exc}"
            ) from exc

    def create_standalone(self):
        if not self.grammar_path.is_file():
            raise NidavellirFileNotFoundError(
                f"Grammar file not found at {self.grammar_path}"
            )

        try:
            grammar = self.grammar_path.read_text(encoding="utf-8")

            parser = Lark(
                grammar,
                parser="lalr",
                start="start",
            )

            with self.standalone_path.open("w", encoding="utf-8") as output:
                gen_standalone(parser, out=output)

        except Exception as exc:
            raise NidavellirInternalError(
                f"Standalone parser generation failed: {exc}"
            ) from exc

    def check_grammar(self):
        if not self.grammar_path.is_file():
            raise NidavellirFileNotFoundError(
                f"Grammar file not found at {self.grammar_path}"
            )

        try:
            grammar = self.grammar_path.read_text(encoding="utf-8")

            Lark(
                grammar,
                parser="lalr",
                start="start",
            )

        except Exception as exc:
            raise NidavellirInternalError(f"Grammar validation failed: {exc}") from exc

        if not self.standalone_path.is_file():
            print("Standalone parser: NOT GENERATED")
            return

        grammar_mtime = self.grammar_path.stat().st_mtime
        standalone_mtime = self.standalone_path.stat().st_mtime

        if grammar_mtime > standalone_mtime:
            print("Standalone parser: OUTDATED")
        else:
            print("Standalone parser: UP TO DATE")

    def process_grammar(self):
        if not SysArgs.grammar:
            return

        match SysArgs.grammar_command:
            case "compile":
                self.create_standalone()
                self.check_grammar()

            case "update":
                self.create_standalone()
                self.check_grammar()

            case "remove":
                self.remove_standalone()

            case "check":
                self.check_grammar()

            case _:
                raise NidavellirInternalError(
                    f"Unknown grammar command: {SysArgs.grammar_command}"
                )

        sys.exit(0)
