import os
import re
import subprocess
import tempfile
from utils import SysArgs
from pathlib import Path


class GCCHeaderScraper:
    def __init__(self, gcc_path="gcc"):
        self.gcc_path = gcc_path

    def extract_signatures(self, header_name: str) -> dict:
        signatures = {}
        runtime_path = Path(__file__).parent.parent / "runtime"

        gcc_include_flags = [f"-I{p}" for p in SysArgs.include_paths]

        with tempfile.NamedTemporaryFile(
            mode="w+", delete=False, suffix=".info"
        ) as tmp:
            tmp_path = tmp.name

        try:
            cmd = [
                self.gcc_path,
                "-xc",
                "-",
                "-aux-info",
                tmp_path,
                "-fsyntax-only",
                f"-I{runtime_path}",
                *gcc_include_flags,
            ]

            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            include_stmt = f"#include <{header_name}>\n"
            process.communicate(input=include_stmt)

            if not os.path.exists(tmp_path):
                return signatures

            with open(tmp_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            pattern = r"(?:extern|static|inline|\s)*([\w\s\*]+?)\s*(\w+)\s*\((.*?)\)(?:\s*\{|;)"

            for match in re.finditer(pattern, content):
                ret_type, fn_name, args_str = match.groups()

                args_list = [arg.strip() for arg in args_str.split(",") if arg.strip()]

                signatures[fn_name] = {
                    "return": ret_type.strip(),
                    "args": args_list,
                }

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        return signatures


if __name__ == "__main__":
    gcc_header_scraper = GCCHeaderScraper()
    signatures = gcc_header_scraper.extract_signatures("stdio.h")
    print(signatures)
