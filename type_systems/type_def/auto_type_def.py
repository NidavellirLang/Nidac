from ..types import *
from semantic.analyzer.symbol_types import *
from utils.errors import *


def detect_type(value: str):
    try:
        int(value)
        return int
    except ValueError:
        try:
            float(value)
            return float
        except ValueError:
            return str


class AutoTypeDefEngine:
    def __init__(self, sym_tree):
        self.sym_tree = sym_tree

    def process_NoneSymbol(self, sym):
        sym.type = NoneType()

    def process_BooleanSymbol(self, sym):
        sym.type = BooleanType()

    def process_NumberSymbol(self, sym):
        val = detect_type(sym.value)

        with TypeUpdate(sym):
            if val is int:
                sym.type = IntType()
            elif val is float:
                sym.type = FloatType()
            else:
                raise NidavellirTypeError(
                    f"Cannot determine type of number {sym.value}", sym.ast_node.line
                )

    def process_VariableSymbol(self, sym):
        if sym.type is None:
            lk = sym.lookup
            if isinstance(lk, FunctionSymbol):
                type = FuncRefType(lk)
                with TypeUpdate(sym):
                    sym.type = type

                return

            lk_type = lk.type
            if lk_type is None:
                self.process(lk)
                lk_type = lk.type

            if lk_type is None:
                raise NidavellirTypeError(
                    "Cannot determine type of variable", sym.ast_node.line
                )

            with TypeUpdate(sym):
                sym.type = lk_type

    def process_StringSymbol(self, sym):
        pass

    def process_AssignSymbol(self, sym):
        if sym.value is not None:
            if sym.type is not None:
                with TypeUpdate(sym.value):
                    sym.value.type = sym.type

            self.process(sym.value)

            if sym.type is None:
                with TypeUpdate(sym):
                    types = sym.value.type
                    sym.type = types
                    if sym.type is None:
                        raise NidavellirTypeError(
                            f"Cannot determine type of assigned value {sym}",
                            sym.ast_node.line,
                        )
        elif sym.uses:
            infered_types = []
            last_type = None
            for use in sym.uses:
                if use.type is None:
                    self.process(use)

                if use.type is None:
                    raise NidavellirTypeError(
                        "Cannot determine type of assigned value", sym.ast_node.line
                    )

                if last_type is not None and type(last_type) != type(use.type):
                    raise NidavellirTypeError(
                        f"Cannot determine type of assigned value, {last_type} -> {use.type}",
                        sym.ast_node.line,
                    )

                last_type = use.type

                infered_types.append(use.type)

            if infered_types and last_type:
                sym.type = last_type

            else:
                raise NidavellirTypeError(
                    "Cannot determine type of assigned value", sym.ast_node.line
                )

        if sym.field:

            self.process(sym.field)

    def process_DefinitionSymbol(self, sym):
        if sym.type is None:
            self.process(sym.value)
            with TypeUpdate(sym):
                sym.type = sym.value.type
                if sym.type is None:
                    raise NidavellirTypeError(
                        "Cannot determine type of assigned value", sym.ast_node.line
                    )

    def process_BinaryOpSymbol(self, sym):
        expected_type = sym.type

        right = sym.right_sym
        left = sym.left_sym

        if right.type is None:
            self.process(right)

        if left.type is None:
            self.process(left)

        if right.type is None or left.type is None:
            raise NidavellirTypeError(
                "Cannot determine type of binary operation",
                sym.ast_node.line,
            )

        if isinstance(left.type, NumberType) and isinstance(right.type, NumberType):
            if isinstance(expected_type, FloatType):
                result_type = FloatType()
            elif isinstance(left.type, FloatType) or isinstance(right.type, FloatType):
                result_type = FloatType()
            else:
                result_type = left.type

        elif type(left.type) == type(right.type):
            result_type = left.type

        else:
            raise NidavellirTypeError(
                f"Incompatible operand types: {left.type} and {right.type}",
                sym.ast_node.line,
            )

        with TypeUpdate(sym):
            sym.type = result_type

    def process_UnaryOpSymbol(self, sym):
        right = sym.right_sym
        if right.type is None:
            self.process(right)

        if right.type is None:
            raise NidavellirTypeError(
                "Cannot determine type of unary operation", sym.ast_node.line
            )

        with TypeUpdate(sym):
            sym.type = right.type

    def _infer_returns(self, body: list):
        returns = []

        for node in body:
            if isinstance(node, ReturnSymbol):
                returns.append(node)
            elif hasattr(node, "body"):
                returns.extend(self._infer_returns(node.body))

        return returns

    def process_FunctionSymbol(self, sym: FunctionSymbol):
        pass

    def _process_FunctionSymbol(self, sym):
        arg_types = {}
        sym.is_called = True

        for call in sym.uses:
            if not isinstance(call, (CallSymbol, ConstructorCallSymbol)):
                continue

            offset = getattr(call, "arg_offset", 0)

            for idx, arg in enumerate(call.args):
                if arg.type is None:
                    self.process(arg)

                arg_type = arg.type
                if arg_type is None:
                    raise NidavellirTypeError(
                        f"Cannot infer argument type at position {idx} in call {call.name}",
                        sym.ast_node.line,
                    )

                if (previous_type := arg_types.get(idx + offset)) is not None:
                    if arg_type != previous_type:
                        raise NidavellirTypeError(
                            f"Incompatible argument types in call {call.name}: {arg_type} and {previous_type}",
                            sym.ast_node.line,
                        )

                arg_types[idx + offset] = arg_type

        for idx, arg in enumerate(sym.args):
            if arg.type is None:
                arg_type = arg_types.get(idx)
                if arg_type is None:
                    continue

                with TypeUpdate(arg):
                    arg.type = arg_type

        self.process_from_list(sym.body)

        inferred_type = None
        for node in self._infer_returns(sym.body):
            if inferred_type is None:
                inferred_type = node.type
                continue

            if type(node.type) != type(inferred_type):
                raise NidavellirTypeError(
                    f"Incompatible return types in function '{sym.name}': {inferred_type} and {node.type}",
                    sym.ast_node.line,
                )
            inferred_type = node.type

        if inferred_type is not None:
            with TypeUpdate(sym):
                sym.type = inferred_type
        elif sym.type is None:
            with TypeUpdate(sym):
                sym.type = NoneType()

    def process_ReturnSymbol(self, sym):
        if sym.value is None:
            return

        if sym.value.type is None:
            self.process(sym.value)

        if sym.value.type is None:
            raise NidavellirTypeError(
                "Cannot determine type of return value", sym.ast_node.line
            )

        with TypeUpdate(sym):
            sym.type = sym.value.type

    def _get_calls_from_value(self, val_sym):
        uses = val_sym.uses if hasattr(val_sym, "uses") else []
        calls = []
        for use in uses:
            if isinstance(use, CallSymbol):
                calls.append(use)

        return calls

    # returned is_class and lk
    def _get_function_from_target(self, target):
        if isinstance(target, FunctionSymbol):
            return False, target
        elif isinstance(target, ClassSymbol):
            return True, target

        if isinstance(target, VariableSymbol):
            lookup = target.lookup
            if isinstance(lookup, FunctionSymbol):
                return False, lookup
            elif isinstance(lookup, ClassSymbol):
                return True, lookup
            else:
                return self._get_function_from_target(lookup)

        if hasattr(target, "value"):
            return self._get_function_from_target(target.value)

        raise Exception(target, isinstance(target, VariableSymbol))

    def _set_arg_uses(self, sym, uses: list):
        for idx, arg in enumerate(sym.args):
            arg.uses.append(uses[idx])

    def _check_args_counts(self, sym, fn_sym):
        if not hasattr(sym, "args"):
            raise NidavellirInternalError(
                f"Symbol '{sym.ast_node.target}' does not have arguments",
                sym.ast_node.line,
            )

        original_name = fn_sym.ast_node.name
        alias_info = (
            f" (alias of '{original_name}')"
            if sym.ast_node.target != original_name
            else ""
        )

        message = (
            f"Call to function '{sym.ast_node.target}'{alias_info} requires "
            f"{len(fn_sym.args)} arguments, but {len(sym.args)} were provided"
        )

        if len(fn_sym.args) != len(sym.args):
            raise NidavellirTypeError(
                message,
                sym.ast_node.line,
            )

    def process_CallSymbol(self, sym):
        lk = sym.lookup
        if isinstance(lk, FunctionSymbol):
            self._process_FunctionSymbol(lk)
        else:
            is_class, fn = self._get_function_from_target(lk)
            if not is_class:
                self._check_args_counts(sym, fn)

                calls = self._get_calls_from_value(lk)
                for call in calls:
                    arg_uses = []
                    for arg in call.args:
                        arg_uses.append(arg)

                    self._set_arg_uses(fn, arg_uses)

                self._set_arg_uses(fn, sym.args)

                fn.uses.extend(calls)
                self._process_FunctionSymbol(fn)

                if sym.type is None:
                    sym.type = fn.type
            else:
                req_params = fn.params
                init_fn = fn.init_fn
                if init_fn is None and sym.args:
                    raise NidavellirTypeError(
                        f"Cannot call constructor of class '{fn.name}' with arguments",
                        sym.ast_node.line,
                    )
                if req_params is None and sym.args:
                    raise NidavellirTypeError(
                        f"Constructor of class '{fn.name}' requires no arguments",
                        sym.ast_node.line,
                    )

                elif req_params is not None and len(req_params) != len(sym.args):
                    raise NidavellirTypeError(
                        f"Constructor of class '{fn.name}' requires "
                        f"{len(req_params)} arguments, but {len(sym.args)} were provided",
                        sym.ast_node.line,
                    )

                sym.type = ClassType(fn.name)

        if sym.type is None:
            if sym.lookup.type is None:
                self.process(sym.lookup)

            if sym.lookup.type is None:
                raise NidavellirTypeError(
                    "Cannot determine type of call", sym.ast_node.line
                )

            with TypeUpdate(sym):
                sym.type = sym.lookup.type

        if sym.args is not None:
            for arg in sym.args:
                self.process(arg)

    def process_ConstructorCallSymbol(self, sym):
        for arg in sym.args:
            self.process(arg)

        with TypeUpdate(sym):
            sym.type = sym.lookup.type

    def process_ClassSymbol(self, sym):
        self.process_from_list(sym.body)

        for method in sym.method_syms.values():
            self._process_FunctionSymbol(method)

    def process_SelfSymbol(self, sym):
        if sym.class_name is None:
            raise NidavellirTypeError(
                "'self' is only valid inside a class", sym.ast_node.line
            )

        with TypeUpdate(sym):
            sym.type = ClassType(sym.class_name)

    def process_FieldAccessSymbol(self, sym):
        target = sym.target
        if target.type is None:
            self.process(target)

        field = sym.chain

        if isinstance(target.type, ClassType):
            class_sym = self._find_class(target.type.name)
            if class_sym is None:
                raise NidavellirTypeError(
                    f"Class '{target.type.name}' not found", sym.ast_node.line
                )

            field_sym = class_sym.field_syms.get(field.name)
            # raise Exception(class_sym)
            if field_sym is None:
                raise NidavellirTypeError(
                    f"Field '{sym.ast_node.field.name}' not found in class '{target.type.name}'",
                    sym.ast_node.line,
                )

            field.lookup = field_sym
            field.field_name = field_sym.name
            if field_sym.type is None:
                self.process(field_sym)

            if field_sym.type is None:
                raise NidavellirTypeError(
                    f"Cannot determine type of field '{field.name}' in class '{target.type.name}'",
                    sym.ast_node.line,
                )

            with TypeUpdate(field):
                field.type = field_sym.type
                sym.type = field_sym.type

        return

    def _find_class(self, name):
        for sym in self.sym_tree:
            if isinstance(sym, ClassSymbol) and sym.name == name:
                return sym

        return None

    def process_IntrinsicCallSymbol(self, sym):
        args = sym.args
        intrinsic = sym.intrinsic
        self.process_from_list(args)
        if sym.type is None:
            if intrinsic.type is None:
                raise NidavellirTypeError(
                    "Cannot determine type of intrinsic call", sym.ast_node.line
                )

            with TypeUpdate(sym):
                sym.type = intrinsic.type

        if not intrinsic.params.check(args):
            raise NidavellirTypeError(
                f"Invalid arguments for intrinsic '{intrinsic.name}'", sym.ast_node.line
            )

    def process_IfSymbol(self, sym):
        self.process(sym.cond)

        for stmt in sym.body:
            self.process(stmt)

        if sym.elifs is not None:
            for elif_sym in sym.elifs:
                self.process(elif_sym.cond)

                for stmt in elif_sym.body:
                    self.process(stmt)

        if sym.else_body is not None:
            for stmt in sym.else_body:
                self.process(stmt)

        merges = sym.merges
        for merge in merges:
            assign_sym = merge.merge_assign_sym
            self.process(assign_sym)

    def process_ListLiteralSymbol(self, sym):
        for element_sym in sym.elements:
            self.process(element_sym)

        if sym.type is None:
            with TypeUpdate(sym):
                sym.type = ListType()

    def process(self, sym):
        method_name = f"process_{type(sym).__name__}"
        visitor = getattr(self, method_name, None)
        if visitor is None:
            raise NidavellirInternalError(
                f"No visitor method '{method_name}' for symbol", sym.ast_node.line
            )
        return visitor(sym)

    def process_from_list(self, syms):
        for sym in syms:
            self.process(sym)

    def run(self):
        self.process_from_list(self.sym_tree)
