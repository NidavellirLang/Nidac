IGNORED_FIELDS = {
    "uses",
    "lookup" "parent",
    "children",
    "scope_type",
    "__module__",
    "__doc__",
    "__firstlineno__",
    "__static_attributes__",
    "__weakref__",
}


def format_item(item):
    if hasattr(item, "__class__") and item.__class__.__name__.endswith("AST"):
        node_name = item.__class__.__name__
        target = getattr(item, "target", getattr(item, "name", ""))
        target_str = f" ({target})" if target else ""
        return f"<{node_name}{target_str}>"

    return item


def render_node(label, value, prefix="", is_last=True, seen=None):
    seen = frozenset() if seen is None else seen
    branch = "└── " if is_last else "├── "
    child_prefix = prefix + ("    " if is_last else "│   ")

    formatted = format_item(value)
    if isinstance(formatted, str):
        if label is not None:
            return [prefix + branch + f"{label}: {formatted}"]
        return [prefix + branch + formatted]

    if isinstance(value, list):
        label_text = label if label is not None else "list"
        header = prefix + branch + label_text + (":" if value else ": []")
        lines = [header]
        for index, item in enumerate(value):
            item_last = index == len(value) - 1
            lines.extend(render_node(None, item, child_prefix, item_last, seen))
        return lines

    if isinstance(value, dict):
        label_text = label if label is not None else "dict"
        header = prefix + branch + label_text + (":" if value else ": {}")
        lines = [header]
        for index, (key, item) in enumerate(value.items()):
            item_last = index == len(value) - 1
            lines.extend(render_node(str(key), item, child_prefix, item_last, seen))
        return lines

    if type(value).__name__.endswith("Scope"):
        symbols_dict = getattr(value, "symbols", {})
        return render_node(label or "members", symbols_dict, prefix, is_last, seen)

    if hasattr(value, "__dict__"):
        header = f"{label} : {type(value).__name__}" if label else type(value).__name__

        if id(value) in seen:
            return [prefix + branch + header + "  (circular reference)"]

        lines = [prefix + branch + header]
        lines.extend(render_attrs(value, child_prefix, seen | {id(value)}))
        return lines

    if label is not None:
        return [prefix + branch + f"{label}: {value!r}"]

    item_lines = repr(value).splitlines() or [repr(value)]
    lines = [prefix + branch + item_lines[0]]
    lines.extend(child_prefix + line for line in item_lines[1:])
    return lines


def render_attrs(obj, prefix="", seen=None):
    seen = frozenset() if seen is None else seen
    seen = seen | {id(obj)}

    attrs = [
        (key, val)
        for key, val in vars(obj).items()
        if key not in IGNORED_FIELDS and not key.startswith("_")
    ]

    lines = []
    for index, (key, val) in enumerate(attrs):
        lines.extend(render_node(key, val, prefix, index == len(attrs) - 1, seen))
    return lines
