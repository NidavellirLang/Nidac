from .symbol_table import SymbolTableManager
from .tree_printer import render_node
from .symbol_types import *
from nida_ast.base import *
from type_systems.types import *
from utils.errors import *
from ..intrinsics import INTRINSICS


class TreeBuilderHelpers:
    @classmethod
    def check_intrinsic_call(cls, name):
        return name in INTRINSICS


class SymbolTreeBuilder:
    def __init__(self, ast_tree, ctx):
        self.id_alloc = ctx["id_alloc"]
        self.ast_tree = ast_tree
        self.stm = SymbolTableManager()
        self.st = []

        self.visited_imports = set()

        self.current_class_name = None

    def get_id(self, ast):
        id = ast.node_id
        if id is None:
            raise NidavellirInternalError("Node ID is not set", ast.line)

        return id

    def resolve(self, type_val):
        resolved = resolve_type(type_val)

        if resolved is None and isinstance(type_val, str):
            if isinstance(self.stm.lookup_class_name(type_val), ClassSymbol):
                return ClassType(type_val)

        return resolved

    def eval_VariableAST(self, ast):
        var = self.stm.lookup_assignment_name(ast.name)
        if var is None:
            var = self.stm.lookup_func_name(ast.name)

        if isinstance(var, UnavailableSymbol):
            raise NidavellirSemanticError(var.why, ast.line)

        if var is None:
            raise NidavellirNameError(f"Variable '{ast.name}' is not defined", ast.line)

        return VariableSymbol(var.name, var, ast)

    def eval_AssignAST(self, ast):
        return self.stmt_AssignAST(ast)

    def eval_NumberAST(self, ast):
        sym = NumberSymbol(ast.value, ast)
        return sym

    def eval_BinaryOpAST(self, ast):
        left_sym = self.process_eval(ast.left)
        right_sym = self.process_eval(ast.right)

        return BinaryOpSymbol(ast.op, left_sym, right_sym, ast)

    def eval_GroupAST(self, ast):
        return self.process_eval(ast.expr)

    def eval_StringAST(self, ast):
        return StringSymbol(ast.value, ast)

    def eval_NoneAST(self, ast):
        return NoneSymbol(ast)

    def eval_CallAST(self, ast):
        return self.stmt_CallAST(ast)

    def eval_IntrinsicAST(self, ast):
        self.stmt_intrinsic(ast.name, ast.type, ast.args)
        return self.stmt_CallAST(ast)

    def eval_BooleanAST(self, ast):
        return BooleanSymbol(ast.value, ast)

    def eval_UnaryOpAST(self, ast):
        right_sym = self.process_eval(ast.right)

        return UnaryOpSymbol(ast.op, right_sym, ast)

    def eval_ListLiteralAST(self, ast):
        elements = []

        for e in ast.elements:
            element_sym = self.process_eval(e)
            elements.append(element_sym)

        return ListLiteralSymbol(elements, ast)

    def stmt_PassAST(self, ast):
        pass

    def stmt_AssignAST(self, ast):
        target = ast.target
        re_assign = self.stm.lookup_assignment_name(target)
        if isinstance(re_assign, UnavailableSymbol):
            re_assign = None

        assign_id = re_assign.ast_node.node_id if re_assign is not None else ast.node_id
        assign_name = self.id_alloc.name_of(assign_id)

        val_sym = self.process_eval(ast.value) if ast.value is not None else None

        final_sym = AssignSymbol(
            assign_name,
            ast.type,
            val_sym,
            ast,
            re_assign if re_assign is not None else None,
        )

        if final_sym.type is None:
            final_sym.type = self.resolve(ast.type)

        target_sym = re_assign

        if target_sym is not None:
            final_sym.parent_assign = target_sym
            target_sym.uses.append(final_sym)
        elif target != "self":
            self.stm.define_assignment(target, ast.node_id, final_sym)

        if ast.chain:
            raise NidavellirNotImplementedError("Chained assignments")

        return final_sym

    def stmt_DefinitionAST(self, ast):
        lk = self.stm.lookup(ast.target)
        if lk is not None:
            raise NidavellirSemanticError(
                f"Definition of variable '{ast.target}' already exists", ast.line
            )

        val = ast.value
        val_sym = self.process_eval(val)

        self.stm.add_symbol(d := DefinitionSymbol(ast.target, ast.type, val_sym, ast))
        return d

    def stmt_FunctionAST(self, ast):
        fn_sym = self.stm.lookup_func_name(ast.name)
        fn_id = self.get_id(ast)
        fn_name = self.id_alloc.name_of(fn_id)

        if fn_sym is None:
            fn_sym = FunctionSymbol(fn_name, ast.type, None, ast)
            self.stm.define_func(ast.name, self.get_id(ast), fn_sym)

        fn_sym.ast_node = ast
        fn_sym.type = self.resolve(ast.type)

        self.stm.enter_scope()

        params = []
        for param in ast.args:
            res = self.process_eval(param)
            if res is not None:
                params.append(res)

        fn_sym.args = params

        res = self.process_from_list(ast.body)
        fn_sym.body = res
        fn_sym.returned.extend([r for r in res if isinstance(r, ReturnSymbol)])

        self.stm.exit_scope()

        return fn_sym

    def stmt_ReturnAST(self, ast):
        val = ast.value
        if val is not None:
            val = self.process_eval(ast.value)

        return ReturnSymbol(val, ast)

    def process_call_args(self, args, lookup, func_name, is_intrinsic=False, skip=0):
        params = []
        arg_symbols = self._arg_symbols(lookup)[skip:]

        for idx, arg in enumerate(args):
            res = self.process_eval(arg)

            lookup_func_arg = None
            if not is_intrinsic:
                if idx >= len(arg_symbols):
                    raise NidavellirSemanticError(
                        f"Function '{func_name}' received too many arguments", arg.line
                    )

                lookup_func_arg = arg_symbols[idx]

            if res is not None:
                params.append(res)

            if (
                lookup_func_arg is not None
                and res is not None
                and not is_intrinsic
                and not isinstance(lookup_func_arg, SelfSymbol)
            ):
                lookup_func_arg.uses.append(res)

        return params

    def _arg_symbols(self, lookup):
        if isinstance(lookup, ClassSymbol):
            init_sym = lookup.method_syms.get("__init__")

            if init_sym is None:
                return []

            return init_sym.args or []

        return getattr(lookup, "args", None) or []

    def process_intrinsic_call(self, ast):
        intrinsic = INTRINSICS[ast.target]
        name = intrinsic.name
        args = ast.args
        n_args = self.process_call_args(args, intrinsic, name, is_intrinsic=True)

        return IntrinsicCallSymbol(intrinsic, name, n_args, ast)

    def stmt_CallAST(self, ast):
        func_name = ast.target

        if ast.chain:
            raise NidavellirNotImplementedError("Chained calls", ast.line)

        lookup = self.stm.lookup_func_name(func_name)
        is_intrinsic = TreeBuilderHelpers.check_intrinsic_call(func_name)
        if is_intrinsic:
            return self.process_intrinsic_call(ast)

        skip = False

        if lookup is None:
            lookup = self.stm.lookup_class_name(func_name)

        if lookup is None:
            skip = True
            lookup = self.stm.lookup_assignment_name(func_name)

        if lookup is None:
            raise NidavellirNameError(
                f"Function '{func_name}' is not defined", ast.line
            )

        params = []
        if not skip:
            params = self.process_call_args(ast.args, lookup, func_name, skip=skip)
        else:
            for arg in ast.args:
                res = self.process_eval(arg)
                params.append(res)

        sym = CallSymbol(func_name, params, lookup, ast)
        lookup.uses.append(sym)

        return sym

    def stmt_ForAST(self, ast):
        self.stm.enter_scope()
        target = self.process_stmt(ast.target)

        source = ast.source
        loop_count = None
        if isinstance(source, (CallAST, IntrinsicAST, IntrinsicCallAST)):
            target_fn = getattr(source, "target", getattr(source, "name", None))
            args = getattr(source, "args", [])
            if target_fn == "range" and args:
                if isinstance(args[0], NumberAST):
                    loop_count = args[0].value
                    loop_count = int(loop_count)
                else:
                    loop_count = Infinity
            else:
                raise NidavellirNotImplementedError(
                    f"For loop source '{target_fn}' is not implemented", ast.source.line
                )
        else:
            raise NidavellirNotImplementedError(
                f"For loop source '{type(source).__name__}' is not implemented",
                ast.source.line,
            )

        target.uses.append(NumberSymbol(0, ast))
        target.uses.append(NumberSymbol(loop_count, ast))

        body = []
        for b in ast.body:
            body.append(self.process_stmt(b))

        self.stm.exit_scope()

        # raise Exception(ast)
        return ForSymbol(target, source, body, loop_count, ast)

    def process_branch(self, body, scope_type):
        scope = self.stm.enter_scope(scope_type)

        symbols = self.process_from_list(body)

        self.stm.exit_scope()

        assignments = scope.registry.norm_assignments

        return symbols, scope, assignments

    def extend_dicts(self, root, ext):
        for k, v in ext.items():
            if k in root:
                continue

            root[k] = v

    def process_elifs(self, elifs) -> tuple[list, list]:
        if not elifs or elifs is None:
            return None, None

        elif_assignments = []
        elif_syms = []
        for elf in elifs:
            cond_sym = self.process_eval(elf.cond)
            body_sym, scope, assignments = self.process_branch(elf.body, "elif")
            elif_syms.append(ElifSymbol(cond_sym, body_sym, elf, scope))

            elif_assignments.append(assignments)

        return elif_assignments, elif_syms

    def check_name_exists_from_all_elifs(self, elif_assigns, name):
        for elif_assign in elif_assigns:
            if name not in elif_assign:
                return False

        return True

    def link_merge(self, assign, name_assign):
        if isinstance(assign, MergeAssignmentSymbol):
            assign = assign.merge_assign_sym

        if not isinstance(assign, AssignSymbol):
            return

        merge_assign = name_assign.get(assign.ast_node.target)

        if merge_assign is None:
            return

        previous_merge = assign.is_re_assign

        if previous_merge is not None and previous_merge is not merge_assign:
            previous_merge.name = merge_assign.name
            previous_merge.is_re_assign = merge_assign

            for use in previous_merge.uses:
                use.name = merge_assign.name
                use.is_re_assign = merge_assign

                if use not in merge_assign.uses:
                    merge_assign.uses.append(use)

            previous_merge.uses.clear()

        assign.is_re_assign = merge_assign
        assign.name = merge_assign.name

        if assign not in merge_assign.uses:
            merge_assign.uses.append(assign)

    def create_merges(self, assignments, branches):
        merges = []
        name_assign = {}

        for name, source in assignments.items():
            if isinstance(source, MergeAssignmentSymbol):
                source = source.final_sym

            ast = source.ast_node

            final_sym = AssignSymbol(
                self.id_alloc.anon(),
                ast.type,
                None,
                ast,
                None,
            )

            name_assign[name] = final_sym

            merges.append(
                MergeAssignmentSymbol(
                    final_sym,
                    ast,
                    name,
                )
            )

        for branch in branches:
            for assign in branch.values():
                self.link_merge(assign, name_assign)

        return merges

    def process_ifs_assignments(
        self, if_assigns: dict, elif_assigns: list, else_assigns: dict
    ):
        branches = [if_assigns]

        if elif_assigns:
            branches.extend(elif_assigns)

        branches.append(else_assigns or {})

        all_names = set()

        for branch in branches:
            all_names.update(branch)

        assign_merge = {}
        unavailable = {}

        for name in all_names:
            sources = [branch[name] for branch in branches if name in branch]

            if len(sources) == len(branches):
                assign_merge[name] = sources[0]
            else:
                source = sources[0]

                if isinstance(source, MergeAssignmentSymbol):
                    source = source.final_sym

                unavailable[name] = UnavailableSymbol(
                    "This variable is declared within an if statement, "
                    "but is not defined in every branch.",
                    source.ast_node,
                )

        for key, val in unavailable.items():
            self.stm.define_assignment_norm(key, val)

        for key, val in assign_merge.items():
            self.stm.define_assignment_norm(key, val)

        return self.create_merges(assign_merge, branches)

    def stmt_IfAST(self, ast):
        cond_sym = self.process_eval(ast.cond)

        body_sym, body_scope, if_assignments = self.process_branch(ast.body, "if")

        elif_assignments, elif_syms = self.process_elifs(ast.elifs)

        else_body = None
        else_scope = None
        else_assignments = None

        if ast.else_body is not None:
            else_body, else_scope, else_assignments = self.process_branch(
                ast.else_body.body, "else"
            )

        merges = self.process_ifs_assignments(
            if_assignments, elif_assignments, else_assignments or {}
        )

        return IfSymbol(
            cond_sym,
            body_sym,
            elif_syms,
            else_body,
            ast,
            body_scope,
            else_scope,
            merges,
        )

    def stmt_WhileAST(self, ast):
        cond = ast.cond
        body = ast.body

        cond_sym = self.process_eval(cond)
        body_sym = self.process_from_list(body)

        return WhileSymbol(cond_sym, body_sym, ast)

    def stmt_ImportAST(self, ast):
        module = ast.resolved_module

        if module is None:
            return

        if module in self.visited_imports:
            return

        self.visited_imports.add(module)

        st = self.process_from_list(module.asts)
        self.st.extend(st)

    def stmt_ClassAST(self, ast):
        name = ast.name
        id = self.get_id(ast)

        class_sym = self.stm.lookup_class_name(name)

        if class_sym is None:
            class_sym = ClassSymbol(name, ast)
            self.stm.define_class(name, id, class_sym)

        class_sym.ast_node = ast

        self.stm.enter_scope()
        self.current_class_name = name

        for b in ast.body:
            res = self.process_stmt(b)
            if res is not None:
                class_sym.body.append(res)

            if isinstance(b, AssignAST):
                if b.chain:
                    class_sym.fields[b.chain[0]] = b
                else:
                    class_sym.fields[b.target] = b

                class_sym.field_syms[b.target] = res
            elif isinstance(b, FunctionAST):
                fn_res = res
                if b.name == "__init__":
                    class_sym.init_fn = fn_res
                    params = []
                    for p in b.args:
                        p_res = self.process_stmt(p)
                        if not isinstance(p, SelfAST):
                            params.append(p_res)

                    class_sym.params = params

                class_sym.methods[b.name] = b
                class_sym.method_syms[b.name] = res

                for stmt in b.body:
                    if isinstance(stmt, AssignAST) and stmt.chain:
                        class_sym.fields.setdefault(stmt.chain[0], stmt)

        self.current_class_name = None
        self.stm.exit_scope()

        return class_sym

    def eval_IdentifierAST(self, ast):
        name = ast.name
        return IdentifierSymbol(name, ast)

    def eval_FieldAccessAST(self, ast):
        target = ast.target
        field = ast.field

        field_sym = self.process_eval(field)
        target_sym = self.process_eval(target)

        return FieldAccessSymbol(target_sym, field_sym, ast)

    def eval_SelfAST(self, ast):
        if self.current_class_name is None:
            raise NidavellirSemanticError("Cannot use self outside of class", ast.line)

        return SelfSymbol(ast, self.current_class_name)

    def process_eval(self, ast):
        method_name = f"eval_{type(ast).__name__}"
        visitor = getattr(self, method_name, None)
        if visitor is None:
            raise NidavellirSemanticError(f"No function named {method_name}", ast.line)

        res = visitor(ast)
        id = self.get_id(ast)
        self.stm.define_symbol_id(id, res)
        return res

    def process_stmt(self, ast):
        method_name = f"stmt_{type(ast).__name__}"
        visitor = getattr(self, method_name, None)
        if visitor is None:
            raise NidavellirSemanticError(f"No function named {method_name}", ast.line)

        res = visitor(ast)
        id = self.get_id(ast)
        self.stm.define_symbol_id(id, res)

        return res

    def process_from_list(self, asts):
        st = []
        for ast in asts:
            self.type_analysis(ast)
            res = self.process_stmt(ast)
            if res is not None:
                st.append(res)

        return st

    def type_analysis(self, ast):
        if hasattr(ast, "type"):
            types = ast.type
            if isinstance(types, str):
                lk_c = self.stm.lookup_class_name(types)
                if lk_c is not None:
                    cl_type = ClassType(types)
                else:
                    ast.type = resolve_type(ast.type)

        if hasattr(ast, "body"):
            for b in ast.body:
                self.type_analysis(b)

        if hasattr(ast, "args"):
            for a in ast.args:
                self.type_analysis(a)

    def run(self):
        # self.declare(self.ast_tree)

        res = self.process_from_list(self.ast_tree)
        # breakpoint()
        self.st.extend(res)

    def print_scopes(self, st=None):
        print("SymbolTree")
        st = st or self.st
        lines = render_node("st", st, prefix="", is_last=True)
        for line in lines:
            print(line)

    def print_ast_tree(self):
        print(self.ast_tree)
