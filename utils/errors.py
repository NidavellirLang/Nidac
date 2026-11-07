import sys
from .sys_args_parser import SysArgs


# nidavellir error handler
def exception_handler(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, NidavellirError) and not SysArgs.verbose_errors:
        print(exc_value)
    else:
        sys.__excepthook__(exc_type, exc_value, exc_traceback)


sys.excepthook = exception_handler


class Line:
    def __init__(self, lines, line, col_start, col_end):
        self.lines = lines
        self.line = line
        self.col_start = col_start
        self.col_end = col_end

    def __repr__(self):
        return f"Line({self.line}, {self.col_start}, {self.col_end})"


RED = "\033[31m"
BRIGHT_RED = "\033[91m"
CYAN = "\033[96m"
YELLOW = "\033[33m"
GRAY = "\033[90m"
BOLD = "\033[1m"
RESET = "\033[0m"


class NidavellirError(Exception):

    def __init__(self, message, line=None):
        self.message = message
        self.line = line
        super().__init__(message)

    def __str__(self):

        if self.line is None:
            return f"{RED}{BOLD}Compile Error:{RESET} {self.message}"

        location = self.line
        target_line = location.line
        start_line = max(1, target_line - 3)
        end_line = min(len(location.lines), target_line + 3)

        result = [
            f"\n{RED}{BOLD}Compile Error{RESET} " f"{GRAY}(Line {target_line}){RESET}"
        ]

        for i in range(start_line, end_line + 1):
            line_str = location.lines[i - 1].rstrip("\n")

            if i == target_line:
                result.append(f"{RED}{BOLD} {i:3d} |{RESET} {line_str}")

                caret_start = max(0, location.col_start - 1)
                caret_len = max(1, location.col_end - location.col_start)

                result.append(
                    f"{' ' * 6}{' ' * caret_start}"
                    f"{BRIGHT_RED}{BOLD}{'^' * caret_len}{RESET}"
                )
            else:
                result.append(f"{GRAY} {i:3d} |{RESET} {line_str}")

        result.append(f"\n{YELLOW}{self.message}{RESET}")

        return "\n".join(result)


class NidavellirSyntaxError(NidavellirError):
    pass


class NidavellirImportError(NidavellirError):
    pass


class NidavellirSemanticError(NidavellirError):
    pass


class NidavellirTypeError(NidavellirSemanticError):
    pass


class NidavellirNameError(NidavellirSemanticError):
    pass


class NidavellirMemoryError(NidavellirSemanticError):
    pass


class NidavellirCodegenError(NidavellirError):
    pass


class NidavellirInternalError(NidavellirError):
    pass


class NidavellirNotImplementedError(NidavellirError):
    pass


class NidavellirFileNotFoundError(NidavellirError):
    def __init__(self, message, file_path=None, line=None):
        self.file_path = file_path
        super().__init__(message, line)

    def __str__(self):
        parts = [
            f"{BRIGHT_RED}{BOLD}File not found{RESET}",
            f"  {self.message}",
        ]

        if self.file_path:
            location = f"  {GRAY}--> {RESET}{CYAN}{self.file_path}{RESET}"

            if self.line is not None:
                location += f"{GRAY}:{RESET}" f"{YELLOW}{self.line.line}{RESET}"

            parts.append(location)

        return "\n".join(parts)


class NidavellirGccError(NidavellirError):
    def __init__(self, message, stderr=None, returncode=None):
        self.stderr = stderr
        self.returncode = returncode
        super().__init__(message)

    def __str__(self):
        parts = [f"\n{RED}{BOLD}GCC Compilation Error{RESET}"]

        if self.returncode is not None:
            parts.append(f"{GRAY}Exit code: {self.returncode}{RESET}")

        if self.stderr:
            parts.append(self.stderr.rstrip())

        else:
            parts.append(f"{YELLOW}{self.message}{RESET}")

        return "\n".join(parts)
