from pathlib import Path
from utils import SysArgs


class _LarkLoader:

    def __init__(self):
        self.requested_mode = SysArgs.parser_mode

        self._modules = []
        self.is_standalone = False

        self._load()

    def __getattr__(self, name):
        return self.get(name)

    def load_default(self):
        try:
            import lark
            import lark.indenter

            return [lark, lark.indenter]
        except ImportError:
            print("Fallback: lark parser not found")
            return None

    def load_standalone(self):
        try:
            from . import standalone_parser

            return [standalone_parser]
        except ImportError:
            print("Fallback: standalone parser not found")
            return None

    def load_parser(self, retry=0):
        modules = None
        is_standalone = False

        match retry:
            case 0:
                modules = (
                    self.load_default() if self.requested_mode == "dynamic" else None
                )
            case 1:
                modules = self.load_standalone()
                is_standalone = True
            case 2:
                modules = self.load_default()
            case _:
                raise RuntimeError("Cannot load parser")

        if modules is None:
            return self.load_parser(retry + 1)

        return is_standalone, modules

    def _load(self):
        is_standalone, modules = self.load_parser()

        self._modules.extend(modules)
        self.is_standalone = is_standalone

        if SysArgs.verbose_logs:
            print("Selected parser:  ", "Native" if is_standalone else "Dynamic")
            print(
                "Requested parser: ",
                "Dynamic" if self.requested_mode == "dynamic" else "Native",
            )

    def _get(self, key):
        find = None
        for module in self._modules:
            find = getattr(module, key, None)
            if find is not None:
                break

        return find

    def get(self, key):
        val = self._get(key)

        if val is None:
            raise AttributeError(f"{key!r} not found in LarkLoader")

        return val


LarkLoader = _LarkLoader()
