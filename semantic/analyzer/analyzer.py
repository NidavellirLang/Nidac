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

    def create_class_type(self, current=None):
        if current is None:
            current = self.current_class_name

        if current is None:
            raise NidavellirInternalError("Class name is not set", 0)

        return ClassType(current)

    def eval_BooleanAST(self, ast):
        return BooleanSymbol(ast.value, ast_node=ast)

    def eval_NumberAST(self, ast):
        sym = NumberSymbol(ast.value, ast_node=ast)
        return sym

    def eval_StringAST(self, ast):
        return StringSymbol(ast.value, ast_node=ast)

    def eval_NoneAST(self, ast):
        return NoneSymbol(ast_node=ast)

    def stmt_SelfAST(self, ast):
        return self.eval_SelfAST(ast)

    def stmt_PassAST(self, ast):
        pass

    def eval_VariableAST(self, ast):
        name = ast.name
        if name == "self":
            if self.current_class_name is None:
                raise NidavellirSemanticError(
                    "self is only allowed inside class", ast.line
                )

            class_type = self.create_class_type()
            classes = self.stm.lookup_class_name(self.current_class_name)
            vs = VariableSymbol(name, classes, ast_node=ast)
            vs.type = class_type
            return vs

        var = self.stm.lookup_assignment_name(ast.name)

        if var is None:
            var = self.stm.lookup_func_name(ast.name)

        if isinstance(var, UnavailableSymbol):
            raise NidavellirSemanticError(var.why, ast.line)

        if var is None:
            raise NidavellirNameError(f"Variable '{ast.name}' is not defined", ast.line)

        return VariableSymbol(var.name, var, ast_node=ast)

    def eval_AssignAST(self, ast):
        return self.stmt_AssignAST(ast)

    def eval_BinaryOpAST(self, ast):
        op = ast.op
        left_sym = self.process_eval(ast.left)
        right_sym = self.process_eval(ast.right)

        return BinaryOpSymbol(op, left_sym, right_sym, ast_node=ast)

    def eval_GroupAST(self, ast):
        return self.process_eval(ast.expr)

    def eval_CallAST(self, ast):
        return self.stmt_CallAST(ast)

    def eval_IntrinsicAST(self, ast):
        self.stmt_intrinsic(ast.name, ast.type, ast.args)
        return self.stmt_CallAST(ast)

    def eval_SelfAST(self, ast):
        if self.current_class_name is None:
            raise NidavellirSemanticError("Cannot use self outside of class", ast.line)

        self_sym = SelfSymbol(ast, self.current_class_name, ast_node=ast)
        self_sym.type = self.create_class_type()
        return self_sym

    def eval_IdentifierAST(self, ast):
        name = ast.name
        return IdentifierSymbol(name, ast_node=ast)

    def eval_UnaryOpAST(self, ast):
        right_sym = self.process_eval(ast.right)

        return UnaryOpSymbol(ast.op, right_sym, ast_node=ast)

    def eval_ListLiteralAST(self, ast):
        elements = []

        for e in ast.elements:
            element_sym = self.process_eval(e)
            elements.append(element_sym)

        return ListLiteralSymbol(elements, ast_node=ast)

    def stmt_AssignAST(self, ast):
        target = ast.target
        parent_assign = self.stm.lookup_assignment_name(target)
        if isinstance(parent_assign, UnavailableSymbol):
            parent_assign = None

        assign_id = (
            parent_assign.ast_node.node_id if parent_assign is not None else ast.node_id
        )
        assign_name = self.id_alloc.name_of(assign_id)

        val_sym = self.process_eval(ast.value) if ast.value is not None else None

        final_sym = AssignSymbol(
            name=assign_name,
            value=val_sym,
            parent_assign=parent_assign,
            type=ast.type,
            ast_node=ast,
        )

        if final_sym.type is None:
            final_sym.type = self.resolve(ast.type)

        target_sym = parent_assign

        if target_sym is not None:
            final_sym.parent_assign = target_sym
            target_sym.uses.append(final_sym)
        elif target != "self":
            self.stm.define_assignment(target, ast.node_id, final_sym)

        field = ast.field
        field_sym = self.process_eval(field) if field is not None else None

        if field_sym is not None:
            final_sym.field = field_sym

        return final_sym

    def stmt_DefinitionAST(self, ast):
        lk = self.stm.lookup(ast.target)
        if lk is not None:
            raise NidavellirSemanticError(
                f"Definition of variable '{ast.target}' already exists", ast.line
            )

        val = ast.value
        val_sym = self.process_eval(val)
        # TODO: impl
        # self.stm.add_symbol(d := DefinitionSymbol(ast.target, ast.type, val_sym, ast))
        return NotImplemented

    def stmt_FunctionAST(self, ast):
        fn_id = self.get_id(ast)
        fn_name = self.id_alloc.name_of(fn_id)

        fn_sym = self.stm.lookup_func_name(ast.name)

        if fn_sym is None:
            fn_sym = FunctionSymbol(
                fn_name,
                type=self.resolve(ast.type),
                ast_node=ast,
            )
            self.stm.define_func(ast.name, fn_id, fn_sym)
        else:
            fn_sym.type = self.resolve(ast.type)
            fn_sym.ast_node = ast

        self.stm.enter_scope()

        params = []
        for param in ast.args:
            res = self.process_eval(param)

            if res is not None:
                params.append(res)

        fn_sym.args = params

        fn_sym.body = self.process_from_list(ast.body)

        for symbol in fn_sym.body:
            if isinstance(symbol, ReturnSymbol):
                fn_sym.returned.append(symbol)

        self.stm.exit_scope()

        return fn_sym

    def stmt_ReturnAST(self, ast):
        val = ast.value
        if val is not None:
            val = self.process_eval(ast.value)

        return ReturnSymbol(value=val, ast_node=ast)

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

    def link_uses_from_class_call(self, call_args, init_fn, lookup):
        for idx, ca in enumerate(call_args):
            if isinstance(ca, SelfSymbol):
                continue

            lookup_func_arg = init_fn.args[idx + 1]
            if isinstance(lookup_func_arg, SelfSymbol):
                raise

            lookup_func_arg.uses.append(ca)

    def _arg_symbols(self, lookup):
        if isinstance(lookup, ClassSymbol):
            init_sym = lookup.method_syms.get("__init__")

            if init_sym is None:
                return []

            return init_sym.args or []

        return getattr(lookup, "args", None) or []

    # TODO: impl
    def process_intrinsic_call(self, ast):
        intrinsic = INTRINSICS[ast.target]
        name = intrinsic.name
        args = self.process_call_args(ast.args, intrinsic, name, is_intrinsic=True)

        return IntrinsicCallSymbol(
            name=name, args=args, intrinsic=intrinsic, ast_node=ast
        )

    def stmt_CallAST(self, ast):
        func_name = ast.target

        if ast.chain:
            raise NidavellirNotImplementedError("Chained calls", ast.line)

        if TreeBuilderHelpers.check_intrinsic_call(func_name):
            return self.process_intrinsic_call(ast)

        lookup = self.stm.lookup_func_name(func_name)
        is_class = False
        skip_arg_processing = False

        if lookup is None:
            lookup = self.stm.lookup_class_name(func_name)
            is_class = lookup is not None

        if lookup is None:
            lookup = self.stm.lookup_assignment_name(func_name)
            skip_arg_processing = True

        if lookup is None:
            raise NidavellirNameError(
                f"Function '{func_name}' is not defined",
                ast.line,
            )

        params = []

        if skip_arg_processing:
            for arg in ast.args:
                params.append(self.process_eval(arg))
        else:
            params = self.process_call_args(ast.args, lookup, func_name)

        sym = CallSymbol(
            name=func_name,
            args=params,
            lookup=lookup,
            ast_node=ast,
        )

        lookup.uses.append(sym)

        if is_class:
            init_fn = lookup.init_fn

            if init_fn is not None:
                init_fn.uses.append(sym)
                self.link_uses_from_class_call(params, init_fn, lookup)

        return sym

    # TODO: impl
    # def stmt_ForAST(self, ast):

    def process_branch(self, body, scope_type):
        scope = self.stm.enter_scope(scope_type)

        symbols = self.process_from_list(body)

        self.stm.exit_scope()

        assignments = scope.registry.norm_assignments

        return symbols, scope, assignments

    # TODO: implement if, elif, else

    # def extend_dicts(self, root, ext):
    #     for k, v in ext.items():
    #         if k in root:
    #             continue

    #         root[k] = v

    # def process_elifs(self, elifs) -> tuple[list, list]:
    #     if not elifs or elifs is None:
    #         return None, None

    #     elif_assignments = []
    #     elif_syms = []
    #     for elf in elifs:
    #         cond_sym = self.process_eval(elf.cond)
    #         body_sym, scope, assignments = self.process_branch(elf.body, "elif")
    #         elif_syms.append(ElifSymbol(cond_sym, body_sym, elf, scope))

    #         elif_assignments.append(assignments)

    #     return elif_assignments, elif_syms

    # def check_name_exists_from_all_elifs(self, elif_assigns, name):
    #     for elif_assign in elif_assigns:
    #         if name not in elif_assign:
    #             return False

    #     return True

    # def link_merge(self, assign, name_assign):
    #     if isinstance(assign, MergeAssignmentSymbol):
    #         assign = assign.merge_assign_sym

    #     if not isinstance(assign, AssignSymbol):
    #         return

    #     merge_assign = name_assign.get(assign.ast_node.target)

    #     if merge_assign is None:
    #         return

    #     previous_merge = assign.is_re_assign

    #     if previous_merge is not None and previous_merge is not merge_assign:
    #         previous_merge.name = merge_assign.name
    #         previous_merge.is_re_assign = merge_assign

    #         for use in previous_merge.uses:
    #             use.name = merge_assign.name
    #             use.is_re_assign = merge_assign

    #             if use not in merge_assign.uses:
    #                 merge_assign.uses.append(use)

    #         previous_merge.uses.clear()

    #     assign.is_re_assign = merge_assign
    #     assign.name = merge_assign.name

    #     if assign not in merge_assign.uses:
    #         merge_assign.uses.append(assign)

    # def create_merges(self, assignments, branches):
    #     merges = []
    #     name_assign = {}

    #     for name, source in assignments.items():
    #         if isinstance(source, MergeAssignmentSymbol):
    #             source = source.final_sym

    #         ast = source.ast_node

    #         final_sym = AssignSymbol(
    #             self.id_alloc.anon(),
    #             ast.type,
    #             None,
    #             ast,
    #             None,
    #         )

    #         name_assign[name] = final_sym

    #         merges.append(
    #             MergeAssignmentSymbol(
    #                 final_sym,
    #                 ast,
    #                 name,
    #             )
    #         )

    #     for branch in branches:
    #         for assign in branch.values():
    #             self.link_merge(assign, name_assign)

    #     return merges

    # def process_ifs_assignments(
    #     self, if_assigns: dict, elif_assigns: list, else_assigns: dict
    # ):
    #     branches = [if_assigns]

    #     if elif_assigns:
    #         branches.extend(elif_assigns)

    #     branches.append(else_assigns or {})

    #     all_names = set()

    #     for branch in branches:
    #         all_names.update(branch)

    #     assign_merge = {}
    #     unavailable = {}

    #     for name in all_names:
    #         sources = [branch[name] for branch in branches if name in branch]

    #         if len(sources) == len(branches):
    #             assign_merge[name] = sources[0]
    #         else:
    #             source = sources[0]

    #             if isinstance(source, MergeAssignmentSymbol):
    #                 source = source.final_sym

    #             unavailable[name] = UnavailableSymbol(
    #                 "This variable is declared within an if statement, "
    #                 "but is not defined in every branch.",
    #                 source.ast_node,
    #             )

    #     for key, val in unavailable.items():
    #         self.stm.define_assignment_norm(key, val)

    #     for key, val in assign_merge.items():
    #         self.stm.define_assignment_norm(key, val)

    #     return self.create_merges(assign_merge, branches)

    # def stmt_IfAST(self, ast):
    #     cond_sym = self.process_eval(ast.cond)

    #     body_sym, body_scope, if_assignments = self.process_branch(ast.body, "if")

    #     elif_assignments, elif_syms = self.process_elifs(ast.elifs)

    #     else_body = None
    #     else_scope = None
    #     else_assignments = None

    #     if ast.else_body is not None:
    #         else_body, else_scope, else_assignments = self.process_branch(
    #             ast.else_body.body, "else"
    #         )

    #     merges = self.process_ifs_assignments(
    #         if_assignments, elif_assignments, else_assignments or {}
    #     )

    #     return IfSymbol(
    #         cond_sym,
    #         body_sym,
    #         elif_syms,
    #         else_body,
    #         ast,
    #         body_scope,
    #         else_scope,
    #         merges,
    #     )

    # TODO: impl
    # def stmt_WhileAST(self, ast):
    #     cond = ast.cond
    #     body = ast.body

    #     cond_sym = self.process_eval(cond)
    #     body_sym = self.process_from_list(body)

    #     return WhileSymbol(cond_sym, body_sym, ast)

    # TODO: impl
    # def stmt_ImportAST(self, ast):
    #     module = ast.resolved_module

    #     if module is None:
    #         return

    #     if module in self.visited_imports:
    #         return

    #     self.visited_imports.add(module)

    #     st = self.process_from_list(module.asts)
    #     self.st.extend(st)

    # TODO: impl
    # def stmt_ClassAST(self, ast):
    #     name = ast.name
    #     id = self.get_id(ast)

    #     class_sym = self.stm.lookup_class_name(name)

    #     if class_sym is None:
    #         class_sym = ClassSymbol(name, ast)
    #         self.stm.define_class(name, id, class_sym)

    #     class_sym.ast_node = ast

    #     self.stm.enter_scope()
    #     self.current_class_name = name

    #     for b in ast.body:
    #         res = self.process_stmt(b)
    #         if res is not None:
    #             class_sym.body.append(res)

    #         if isinstance(b, AssignAST):
    #             if b.field:
    #                 raise NidavellirNotImplementedError("Not implemented", b.line)
    #             else:
    #                 class_sym.fields[b.target] = b

    #             class_sym.field_syms[b.target] = res
    #         elif isinstance(b, FunctionAST):
    #             fn_res = res
    #             if b.name == "__init__":
    #                 class_sym.init_fn = fn_res
    #                 params = []
    #                 for p in b.args:
    #                     if not isinstance(p, SelfAST):
    #                         params.append(p)

    #                 class_sym.params = params

    #             class_sym.methods[b.name] = b
    #             class_sym.method_syms[b.name] = res

    #             # for stmt in b.body:
    #             #     if isinstance(stmt, AssignAST) and stmt.chain:
    #             #         class_sym.fields.setdefault(stmt.chain[0], stmt)

    #     self.current_class_name = None
    #     self.stm.exit_scope()

    #     return class_sym

    def eval_FieldAccessAST(self, ast):
        target = ast.target
        field = ast.field

        field_sym = self.process_eval(field)
        target_sym = self.process_eval(target)

        return FieldAccessSymbol(target=target_sym, field=field_sym, ast_node=ast)

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
        res = self.process_from_list(self.ast_tree)
        self.st.extend(res)

    def print_scopes(self, st=None):
        print("SymbolTree")
        st = st or self.st
        lines = render_node("st", st, prefix="", is_last=True)
        for line in lines:
            print(line)

    def print_ast_tree(self):
        print(self.ast_tree)
