from type_systems.types import Infinity
from pathlib import Path


class CType:
    def __str__(self):
        raise NotImplementedError

    def str(self):
        return str(self)

    def required_headers(self) -> set[str]:
        return set()

    def required_sources(self) -> set[Path]:
        return set()


class CTVoid(CType):
    def __str__(self):
        return "void"


class CTNone(CType):
    def __str__(self):
        return "void *"


class CTInt(CType):
    def __init__(self, signed=False, byte_size=None):
        self.signed = signed
        self.byte_size = byte_size

    def required_headers(self):
        if self.byte_size in (1, 2, 4, 8):
            return {"<stdint.h>"}
        return set()

    def __str__(self):
        if self.byte_size is None:
            return "int"

        int_str = "int" if self.signed else "uint"

        if self.byte_size == Infinity:
            return "idyn"

        if self.byte_size in (1, 2, 4, 8):
            return f"{int_str}{self.byte_size * 8}_t"

        raise ValueError(f"Invalid integer byte size: {self.byte_size}")


class CTFloat(CType):
    def __init__(self, byte_size=None):
        self.byte_size = byte_size

    def __str__(self):
        if self.byte_size is None or self.byte_size == 4:
            return "float"
        if self.byte_size == 8:
            return "double"
        raise ValueError(f"Invalid float byte size: {self.byte_size}")


class CTString(CType):
    def required_headers(self):
        return {'"Nida_str.h"'}

    def __str__(self):
        return "Nida_Str"


class CTStruct(CType):
    """A class instance — always handled as a pointer to the struct."""

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return f"{self.name} *"


class CTList(CType):
    def __init__(self, element_type=None):
        self.element_type = element_type

    def required_headers(self):
        headers = {'"dynix_nida.h"'}

        if self.element_type is not None:
            headers.update(self.element_type.required_headers())

        return headers

    def __str__(self):
        return "Nida_List *"


class CTFuncRef(CType):
    def __init__(self, param_types, return_type):
        self.param_types = param_types
        self.return_type = return_type

    def required_headers(self):
        headers = self.return_type.required_headers()

        for param_type in self.param_types:
            headers.update(param_type.required_headers())

        return headers

    def declare(self, name):
        params = ", ".join(str(t) for t in self.param_types) or "void"
        return f"{self.return_type} (*{name})({params})"

    def __str__(self):
        params = ", ".join(str(t) for t in self.param_types) or "void"
        return f"{self.return_type} (*)({params})"
