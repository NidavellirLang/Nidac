from pathlib import Path

from utils.allocators import NodeIdAllocator


class CompilerContext(dict):
    def __init__(self, runtime_path: Path | str | None = None):
        super().__init__(
            id_alloc=NodeIdAllocator(),
            runtime_path=(
                Path(runtime_path).resolve()
                if runtime_path is not None
                else Path(__file__).resolve().parent.parent / "runtime"
            ),
            c_sources=[],
            c_headers=[],
            include_paths=[],
        )

    def add_c_source(self, path: Path | str) -> None:
        path = Path(path).resolve()
        sources = self["c_sources"]

        if path not in sources:
            sources.append(path)

    def add_c_header(self, header: str) -> None:
        headers = self["c_headers"]

        if header not in headers:
            headers.append(header)

    def add_include_path(self, path: Path | str) -> None:
        path = Path(path).resolve()
        paths = self["include_paths"]

        if path not in paths:
            paths.append(path)
