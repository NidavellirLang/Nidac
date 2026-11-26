from pathlib import Path

from AST.base import *
from .analyzer import check_header_exists
from utils import SysArgs


def get_nidac():
    if (nidac := SysArgs.nidac_ptr) is not None:
        return nidac

    raise RuntimeError("No Nidac instance")


class ModuleOBJ:
    def __init__(self, name, path):
        self.name = name
        self.path = Path(path).resolve()

        self.asts = []
        self.hirs = []
        self.lirs = []
        self.c_code = None
        self.header_code = None
        self.include_path = None
        self.dependencies = []

        self.state = "new"

    def __repr__(self):
        return f"<Module '{self.name}' path='{self.path.name}'>"


class ImportSystem:
    def __init__(self, root_path, root_asts):
        self.root_path = Path(root_path).resolve()
        self.root_asts = root_asts

        self.modules = {}

        self.root_dependencies = []

        self.ordered_modules = []

        self.run()

    def run(self):
        self.root_dependencies = self.scan_imports(self.root_asts)
        self.order_modules()

    def get_source_code(self, path):
        if not path.is_file():
            return None

        return path.read_text(encoding="utf-8")

    def scan_imports(self, asts, owner=None):
        dependencies = []

        for node in asts:
            if not isinstance(node, ImportAST):
                continue

            name = node.module

            if check_header_exists(name):
                continue

            path = self.get_path_from_name(self.name_mapper(name))
            dependency = self.load_module(name, path)

            node.resolved_module = dependency

            if dependency not in dependencies:
                dependencies.append(dependency)

            if owner is not None and dependency not in owner.dependencies:
                owner.dependencies.append(dependency)

        return dependencies

    def load_module(self, name, path):
        path = Path(path).resolve()

        module = self.modules.get(path)
        if module is not None:
            return module

        source_code = self.get_source_code(path)
        if source_code is None:
            raise FileNotFoundError(f"Cannot find module '{name}': {path}")

        module = ModuleOBJ(name, path)

        self.modules[path] = module
        module.state = "loading"

        module.asts = get_nidac().parse_from_source_code(source_code)

        for node in module.asts:
            if isinstance(node, FunctionAST):
                node.is_imported = True

        self.scan_imports(module.asts, owner=module)

        module.state = "loaded"
        return module

    def order_modules(self):
        visiting = set()
        visited = set()
        ordered = []

        def visit(module):
            path = module.path

            if path in visited:
                return

            if path in visiting:
                raise SyntaxError(f"Circular import detected: {module.name} ({path})")

            visiting.add(path)

            for dependency in module.dependencies:
                visit(dependency)

            visiting.remove(path)
            visited.add(path)
            ordered.append(module)

        for module in self.root_dependencies:
            visit(module)

        self.ordered_modules = ordered

    def scan_importable_names(self, asts):
        importable_names = []

        for node in asts:
            if isinstance(node, (ClassAST, FunctionAST)):
                importable_names.append(node.name)

        return importable_names

    def name_mapper(self, name):
        return f"{name}.nida"

    def name_mapper_reverse(self, name):
        return name.removesuffix(".nida")

    def get_path_from_name(self, name):
        return self.root_path / name
