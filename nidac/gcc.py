import subprocess
from pathlib import Path
from utils import SysArgs
from utils.errors import *


def compile_c_file(c_path: str | Path, output_path: str | Path, ctx) -> bool:
    runtime_path = ctx["runtime_path"]

    gcc_include_flags = [
        f"-I{p}" for p in (*SysArgs.include_paths, *ctx["include_paths"])
    ]

    extra_c_sources = [str(f) for f in (*SysArgs.extra_c_files, *ctx["c_sources"])]

    cmd = [
        "gcc",
        str(c_path),
        *extra_c_sources,
        "-o",
        str(output_path),
        "-O2",
        "-Wall",
        "-fdiagnostics-color=always",
        f"-I{runtime_path}",
        *gcc_include_flags,
    ]

    if SysArgs.verbose_errors:
        print(f"Compiling cmd: {' '.join(cmd)}")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise NidavellirGccError(
            "C compilation failed",
            stderr=result.stderr,
            returncode=result.returncode,
        )

    if SysArgs.verbose_errors:
        print(f"Compilation successful: {c_path} -> {output_path}")

    return True


def run_compiled_file(
    bin_path: str | Path,
    args: list[str] = None,
    user_input: str = None,
    timeout: float = 5.0,
) -> int:
    if SysArgs.verbose_errors:
        print("\n\n\n")

    exec_path = Path(bin_path).resolve()

    if not exec_path.exists():
        print(f"Runner error: File not found -> {exec_path}")
        return -1

    cmd = [str(exec_path)]
    if args:
        cmd.extend(args)

    actual_timeout = timeout if timeout and timeout > 0 else None

    try:
        result = subprocess.run(
            cmd,
            input=user_input,
            text=True if user_input else None,
            timeout=actual_timeout,
        )
        return result.returncode

    except subprocess.TimeoutExpired:
        print(f"\nRunner error: Execution timed out after {timeout} seconds.")
        return -1
    except Exception as e:
        print(f"\nRunner error: {e}")
        return -1
