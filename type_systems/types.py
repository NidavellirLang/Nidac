PRIMITIVE_TYPE_FACTORIES = {
    "bool": lambda: BoolType(),
    "u8": lambda: IntType(signed=False, byte_size=1),
    "i8": lambda: IntType(signed=True, byte_size=1),
    "u16": lambda: IntType(signed=False, byte_size=2),
    "i16": lambda: IntType(signed=True, byte_size=2),
    "u32": lambda: IntType(signed=False, byte_size=4),
    "i32": lambda: IntType(signed=True, byte_size=4),
    "u64": lambda: IntType(signed=False, byte_size=8),
    "i64": lambda: IntType(signed=True, byte_size=8),
    # dynamic integer
    "idyn": lambda: IntType(signed=True),
    "f32": lambda: FloatType(byte_size=4),
    "f64": lambda: FloatType(byte_size=8),
    # dynamic float
    "fdyn": lambda: FloatType(),
    "str": lambda: StringType(),
    "None": lambda: NoneType(),
    "void": lambda: NoneType(),
    "dynamic": lambda: DynamicType(),
    "bool": lambda: BooleanType(),
    # user-friendly aliases
    "int": lambda: IntType(signed=True, byte_size=4),
    "float": lambda: FloatType(byte_size=4),
    "String": lambda: StringType(),
    "List": lambda: ListType(),
}

TYPE_RANK = {
    "bool": 0,
    "u8": 1,
    "i8": 2,
    "u16": 3,
    "i16": 4,
    "u32": 5,
    "i32": 6,
    "u64": 7,
    "i64": 8,
    "f32": 9,
    "f64": 10,
    "idyn": 11,
}


def get_type_rank(target_type) -> int:
    return TYPE_RANK.get(str(target_type), -1)


def resolve_type(type_val):
    if type_val is None or isinstance(type_val, Type):
        return type_val

    if isinstance(type_val, str):
        fn = PRIMITIVE_TYPE_FACTORIES.get(type_val, None)
        if fn is not None:
            return fn()

    return None


class Infinity:
    def __repr__(self):
        return "∞ (Nida_Infinity)"


class Type:
    def __repr__(self):
        return f"<Nida Type: {self.__class__.__name__}>"

    def __str__(self):
        return self.__class__.__name__

    def __eq__(self, other):
        if not isinstance(other, Type):
            return NotImplemented

        return str(self) == str(other)


class NumberType(Type):
    pass


class TypeUpdate:
    def __init__(self, sym):
        self.sym = sym

    def __enter__(self):
        return self.sym

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


class DynamicType(Type):
    def __str__(self):
        return "dynamic"


class BoolType(Type):
    def __str__(self):
        return "bool"


class ListType(Type):
    def __init__(self, element_type=None, size=None):
        self.element_type = element_type
        self.size = size

    def __str__(self):
        return "List"


class IntType(NumberType):
    I64_MIN, I64_MAX = -9_223_372_036_854_775_808, 9_223_372_036_854_775_807
    U64_MAX = 18_446_744_073_709_551_615

    def __init__(
        self,
        arg1=None,
        arg2=None,
        signed=True,
        byte_size=DynamicType,
        min_val=None,
        max_val=None,
    ):
        if isinstance(arg1, int) and isinstance(arg2, int):
            self.min_val = arg1
            self.max_val = arg2
            self.signed, self.byte_size = self._infer_bounds(arg1, arg2)
        elif min_val is not None and max_val is not None:
            self.min_val = min_val
            self.max_val = max_val
            self.signed, self.byte_size = self._infer_bounds(min_val, max_val)
        else:
            self.min_val = min_val
            self.max_val = max_val
            self.signed = (
                arg1 if (arg1 is not None and not isinstance(arg1, int)) else signed
            )
            self.byte_size = (
                arg2 if (arg2 is not None and not isinstance(arg2, int)) else byte_size
            )

        self.is_dynamic = (
            self.byte_size == DynamicType
            or self.byte_size == Infinity
            or self.byte_size is None
        )

    @property
    def rank(self) -> int:
        return TYPE_RANK.get(str(self), -1)

    @staticmethod
    def _infer_bounds(min_val: int, max_val: int):
        if min_val >= 0:
            if max_val <= 255:
                return False, 1
            if max_val <= 65_535:
                return False, 2
            if max_val <= 4_294_967_295:
                return False, 4
            if max_val <= IntType.U64_MAX:
                return False, 8
        else:
            if min_val >= -128 and max_val <= 127:
                return True, 1
            if min_val >= -32_768 and max_val <= 32_767:
                return True, 2
            if min_val >= -2_147_483_648 and max_val <= 2_147_483_647:
                return True, 4
            if min_val >= IntType.I64_MIN and max_val <= IntType.I64_MAX:
                return True, 8

        return True, Infinity

    def __str__(self):
        if self.is_dynamic:
            return "idyn"

        prefix = "i" if self.signed else "u"
        return f"{prefix}{self.byte_size * 8}"

    def __eq__(self, other):
        if isinstance(other, IntType):
            return self.signed == other.signed and self.byte_size == other.byte_size
        if isinstance(other, str):
            return str(self) == other
        return False

    def __hash__(self):
        return hash((self.signed, self.byte_size))


class FloatType(NumberType):
    def __init__(self, byte_size=DynamicType):
        self.byte_size = byte_size
        self.is_dynamic = byte_size == DynamicType

    def __str__(self):
        if self.is_dynamic:
            return "fdyn"

        return f"f{self.byte_size * 8}"


class StringType(Type):
    def __init__(self):
        pass

    def __str__(self):
        return "str"


class ArrayType(Type):
    def __init__(self, element_type, size=DynamicType):
        self.element_type = element_type
        self.size = size
        self.is_dynamic = size == DynamicType

    def __str__(self):
        if self.is_dynamic:
            return f"{self.element_type}[]"

        return f"{self.element_type}[{self.size}]"


class NoneType(Type):
    def __str__(self):
        return "None"


class BooleanType(Type):
    def __str__(self):
        return "bool"


class ClassType(Type):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name


class RefType(Type):
    def __init__(self, lk):
        self.lk = lk

    def get_param_types(self):
        params = self.lk.args
        param_types = []
        for p in params:
            type = p.type
            param_types.append(str(type))

        return param_types

    def get_return_type(self):
        return str(self.lk.type) if self.lk.type is not None else None

    def get_types(self):
        return self.get_param_types(), self.get_return_type()

    def __str__(self):
        param_types, return_type = self.get_types()
        params = ", ".join(map(str, param_types))
        return f"{self.__class__.__name__.removesuffix('Type')}[({params}) -> {return_type}]"


class FuncRefType(RefType):
    def __init__(self, lk):
        super().__init__(lk)


class ClassMethodRefType(RefType):
    def __init__(self, lk, instance_lk):
        super().__init__(lk)
        self.instance_lk = instance_lk

    def get_self_instance(self):
        if self.instance_lk is None:
            raise

        return self.instance_lk.name
