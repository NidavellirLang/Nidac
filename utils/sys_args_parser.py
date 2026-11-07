import argparse

import sys

import tempfile

from pathlib import Path


class SysArgsClass:

    def __init__(self, args=None):

        if args is None:
            args = sys.argv[1:]

        parser = argparse.ArgumentParser(
            prog="nidavellir",
            description="Nidavellir Compiler Toolchain",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )

        # Positional Input File
        parser.add_argument(
            "file",
            type=Path,
            nargs="?",
            default=None,
            help="Path to the source .nida file",
        )

        # Include Search Paths (-I / --include-path)
        parser.add_argument(
            "-I",
            "--include-path",
            type=Path,
            action="append",
            dest="include_paths",
            default=[],
            help="Additional search paths for headers and modules (can be specified multiple times)",
        )

        # Extra C Source Files to link (-cfile / --c-file)
        parser.add_argument(
            "-cfile",
            "--c-file",
            type=Path,
            action="append",
            dest="extra_c_files",
            default=[],
            help="Additional .c source files to compile and link into the final binary",
        )

        # Optional Paths
        parser.add_argument(
            "-o",
            "--output",
            type=Path,
            default=None,
            help="Path for compiled binary executable (Defaults to temp directory)",
        )

        parser.add_argument(
            "--emit-c",
            type=Path,
            default=None,
            help="Path for generated C source file (Defaults to temp directory)",
        )

        # Feature flags
        parser.add_argument(
            "-np",
            "--no-print",
            action="store_true",
            help="Disables printing at compile time",
        )

        parser.add_argument(
            "-nr",
            "--no-auto-run",
            action="store_true",
            help="Disables automatic execution of the compiled binary",
        )

        parser.add_argument(
            "-nc",
            "--no-cache",
            action="store_true",
            help="Bypasses build cache and forces full re-compilation",
        )

        parser.add_argument(
            "-nb",
            "--no-binary-compile",
            action="store_true",
            help="Disables invocation of the underlying C compiler (GCC/Clang) and skips binary generation",
        )

        parser.add_argument(
            "-dph",
            "--dump-hir",
            action="store_true",
            help="Dump HIR",
        )

        parser.add_argument(
            "-dpl",
            "--dump-lir",
            action="store_true",
            help="Dump LIR",
        )

        parser.add_argument(
            "-dpa",
            "--dump-ast",
            action="store_true",
            help="Dump AST",
        )

        parser.add_argument(
            "-dpafs",
            "--dump-ast-after-semantic",
            action="store_true",
            help="Dump AST after semantic analysis",
        )

        parser.add_argument(
            "-dpst",
            "--dump-sym-tree",
            action="store_true",
            help="Dump type engine tree (befor type inference)",
        )

        parser.add_argument(
            "-dpt",
            "--dump-type-engine",
            action="store_true",
            help="Dump type engine tree (after type inference)",
        )

        parser.add_argument(
            "-dpc",
            "--dump-c",
            action="store_true",
            help="Dump C nodes",
        )

        parser.add_argument(
            "-sta",
            "--stop-after",
            type=str,
            choices=["hir", "lir", "ast", "semantic", "type-tree", "type-engine", "c"],
            default=None,
            help="Stop after the specified pipeline stage",
        )

        parser.add_argument(
            "-pct",
            "--print-compile-time",
            action="store_true",
            help="Set the time limit for the compilation (in seconds)",
        )

        parser.add_argument(
            "-ve",
            "--verbose-errors",
            action="store_true",
            help="Enable verbose output",
        )

        parser.add_argument(
            "--log-set-sym-attr",
            nargs="+",
            default=[],
            metavar="ATTR",
            help="Log symbol attribute assignments",
        )

        parser.add_argument(
            "--log-uses-appends",
            action="store_true",
            help="Log symbol attribute assignments",
        )

        parsed, _ = parser.parse_known_args(args)

        temp_dir = Path(tempfile.gettempdir())

        file_stem = parsed.file.stem if parsed.file else "snippet"

        if parsed.emit_c is None:
            parsed.emit_c = temp_dir / f"{file_stem}.c"

        if parsed.output is None:
            parsed.output = temp_dir / file_stem

        self.__dict__.update(vars(parsed))
        self.extra_c_includes = []

    def add_include_path(self, path: Path | str) -> None:
        path_obj = Path(path).resolve()

        if path_obj not in self.include_paths:
            self.include_paths.append(path_obj)

    def add_c_file(self, path: Path | str) -> None:
        path_obj = Path(path).resolve()

        if path_obj not in self.extra_c_files:
            self.extra_c_files.append(path_obj)

    def add_extra_c_include(self, name: str) -> None:
        if name not in self.extra_c_includes:
            self.extra_c_includes.append(name)


SysArgs = SysArgsClass()
