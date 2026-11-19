from .c_nodes import *
from .header_nodes import *


class HeaderGenerator:
    def __init__(self, header_name, c_code, ctx):
        self.header_name = header_name
        self.c_code = c_code
        self.ctx = ctx

    def gen_CFunction(self, node):
        name = node.name
        args = node.args
        type = node.type
        return HFunction(name, args, type)

    def gen_CStruct(self, node):
        return HStruct(node.name, node.fields)

    def gen(self, node):
        name = node.__class__.__name__
        func = getattr(self, f"gen_{name}")
        if func is not None:
            return func(node)

    def generate_default_header_dependencies(self):
        ifndef = Hifndef(self.header_name)
        includes = [ifndef]
        for include in self.ctx["extra_c_includes"]:
            name = self.include_name_map(include)
            node = HInclude(name)
            includes.append(node)

        return includes

    def include_name_map(self, name):
        if name.startswith('"'):
            return name
        elif name.startswith("<"):
            return name
        return f'"{name}"'

    def gen_all(self):
        default_dep = self.generate_default_header_dependencies()
        header_nodes = []
        header_nodes.extend(default_dep)
        for c_node in self.c_code:
            res = self.gen(c_node)
            if res is not None:
                header_nodes.append(res)

        header_nodes.append(Hendif())

        return header_nodes

    def header_node_to_str(self, node):
        header_str = ""
        for n in node:
            header_str += n.str()
            if isinstance(n, HFunction):
                header_str += ";\n"

            header_str += "\n"

        return header_str

    def gen_Header(self):
        header_nodes = self.gen_all()
        header_str = self.header_node_to_str(header_nodes)
        return header_str
