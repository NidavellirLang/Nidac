from pathlib import Path

from lexer import Lexer
from nida_ast import Parser
from semantic import semantic_analyze
from import_systems import ImportSystem

from type_systems.main import TypeSystem
from IR_gen import IRGen
from LIR_gen import IRLowerer
from C_gen import C_Gen
from C_gen import HeaderGenerator
from utils import SysArgs, ExecutionTimer, NodeIdAllocator
from utils.errors import NidavellirFileNotFoundError
from .gcc import compile_c_file, run_compiled_file
import sys

sys.set_int_max_str_digits(0)


class Nidac:
    """Nidavellir compiler driver.

    Owns the pipeline state (AST -> HIR -> LIR -> C -> binary) and exposes
    one entry point per stage so callers can stop anywhere in between.
    """

    def __init__(
        self,
        source: str = None,
        file_path: str = None,
        debug: bool = False,
    ):
        self.ctx = {
            "id_alloc": NodeIdAllocator(),
        }

        self.source = source
        self.file_path = file_path
        self.debug = debug

        self.current_path = Path.cwd()

        self.lexer = None
        self.asts = []
        self.imported_modules = []
        self.symbol_table = None

        self.hir = None
        self.lir = None
        self.final_c_code = None
        self.c_gen = None

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------

    def compile(self):
        """Run the whole pipeline, honouring --stop-after and --no-binary-compile."""
        timer = ExecutionTimer()

        timer.start("Lexer")
        self.lex()

        timer.start("Parser")
        self.parse()
        if SysArgs.stop_after == "ast":
            return

        timer.start("Import Systems")
        self.import_systems()

        timer.start("Semantic Analyzer")
        self.analyze()
        if SysArgs.stop_after == "semantic":
            return

        timer.start("Type Engine")
        self.type_def()
        if SysArgs.stop_after in ("type-engine", "type-tree"):
            return

        timer.start("HIR Generator")
        self.HIRGen()
        if SysArgs.stop_after == "hir":
            return

        timer.start("LIR Generator")
        self.LIRGen()
        if SysArgs.stop_after == "lir":
            return

        timer.start("C Generator")
        self.emit_c11()
        if SysArgs.stop_after == "c":
            return

        timer.start("Binary Compiler")
        if not SysArgs.no_binary_compile:
            self.compile_binary()

        if SysArgs.print_compile_time:
            timer.print()

    # ------------------------------------------------------------------
    # Frontend
    # ------------------------------------------------------------------

    def lex(self):
        if self.source is None:
            self.read_file()

        self.lexer = Lexer(self.source)
        return self.lexer

    def parse(self):
        if not self.lexer:
            self.lex()

        parser = Parser(self.lexer, self.ctx)

        self.asts = parser.run()
        if SysArgs.dump_ast:
            print("===== AST =====")
            print(self.asts)

        return self.asts

    def import_systems(self):
        root_path = Path.cwd()
        module_scanner = ImportSystem(root_path, self.asts)
        self.imported_modules = module_scanner.ordered_modules

    def analyze(self):
        if not self.asts:
            self.parse()

        self.symbol_table_b = semantic_analyze(self.asts, self.ctx)
        self.symbol_tree = self.symbol_table_b.st

        # self.ctx["stm"] = self.symbol_table_b.stm

        if SysArgs.dump_ast_after_semantic:
            print("===== AST (after semantic analysis) =====")
            print(self.asts)

        return self.symbol_table

    def type_def(self):
        if not self.symbol_tree:
            self.analyze()

        TypeSystem(self.symbol_tree)

    # ------------------------------------------------------------------
    # Middleend
    # ------------------------------------------------------------------

    def HIRGen(self):
        hir = IRGen(self.asts, self.ctx)
        self.hir = hir.run()

        if SysArgs.dump_hir:
            print("===== HIR =====")
            print(self.hir)

    def LIRGen(self):
        lir = IRLowerer(self.hir)
        self.lir = lir.run()

        if SysArgs.dump_lir:
            print("===== LIR =====")
            print(self.lir)

    # ------------------------------------------------------------------
    # Backend
    # ------------------------------------------------------------------

    def generate_dependencies_c_code(self):
        """Emit one C file + header per imported module into __nidacache__."""
        for module in self.imported_modules:
            if not module.lirs:
                continue

            extra_include = []
            if module.dependencies:
                for dep in module.dependencies:
                    if not dep.include_path:
                        raise Exception(f"No include path for module '{dep.name}'")
                    extra_include.append(dep.include_path.name)

            c_gen = C_Gen(module.lirs, extra_include=extra_include)
            module.c_code = c_gen.gen_from_list(module.lirs)
            c_nodes = c_gen.c_nodes

            h_gen = HeaderGenerator(module.name, c_nodes)
            module.header_code = h_gen.gen_Header()

            c_path = module.path.parent / "__nidacache__" / f"{module.name}.c"
            c_header_path = module.path.parent / "__nidacache__" / f"{module.name}.h"

            module.include_path = c_header_path

            if not module.include_path.exists():
                module.include_path.parent.mkdir(parents=True, exist_ok=True)

            with open(c_path, "w") as f:
                f.write(module.c_code)

            with open(c_header_path, "w") as f:
                f.write(module.header_code)

            SysArgs.add_include_path(c_header_path.parent)
            SysArgs.add_extra_c_include(c_header_path.name)
            SysArgs.add_c_file(c_path)

    def emit_c11(self):
        if self.lir is None:
            self.LIRGen()

        self.generate_dependencies_c_code()

        self.c_gen = C_Gen(self.lir)
        self.final_c_code = self.c_gen.gen_from_list(self.lir)

        if SysArgs.dump_c:
            print("===== C Code =====")
            print(self.final_c_code)
            print("===== C Nodes =====")
            print(self.c_gen.c_nodes)

    def compile_binary(self):
        if self.final_c_code is None:
            self.emit_c11()

        c_path = SysArgs.emit_c

        with open(c_path, "w") as f:
            f.write(self.final_c_code)

        compile_c_file(c_path, SysArgs.output)
        if not SysArgs.no_auto_run:
            self.run_binary(SysArgs.output)

    def run_binary(self, binary_path: str, args: list[str] = None):
        if self.final_c_code is None:
            self.emit_c11()

        run_compiled_file(binary_path, args)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def read_file(self):
        if self.file_path is None:
            raise ValueError("file_path must be provided when source is None")

        path = Path(self.file_path).expanduser().resolve()

        try:
            with path.open("r", encoding="utf-8") as f:
                self.source = f.read()
        except FileNotFoundError:
            raise NidavellirFileNotFoundError(
                "Cannot find source file",
                file_path=str(path),
            ) from None
        except IsADirectoryError:
            raise NidavellirFileNotFoundError(
                "Source path points to a directory, not a file",
                file_path=str(path),
            ) from None

        self.file_path = str(path)

    @staticmethod
    def parse_from_source_code(source_code):
        lexer_obj = Lexer(source_code)
        parser = Parser(lexer_obj)
        parser.parse_all()
        return parser.asts


SysArgs.nidac_ptr = Nidac
