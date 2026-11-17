"""Generic pretty-printing for dataclass trees.

Any dataclass hierarchy can opt in by inheriting from :class:`TreeReprMixin`::

    @dataclass(slots=True, kw_only=True, repr=False)
    class Node(TreeReprMixin):
        name: str
        child: "Node" = None
        items: list["Node"] = dc_field(default_factory=list)

Scalar fields are inlined into the node label (``Node(name='x')``); nested
dataclasses and non-empty lists/tuples become branches. ``__repr__`` renders
the full tree only when ``SysArgs.verbose_logs`` is enabled, otherwise a
compact one-line label.

Hooks to override:

* ``_tree_is_node(value)`` - whether a value should be rendered as a subtree.
* ``_tree_format_value(value)`` - how scalar values are stringified/colored.
* ``_tree_skip_fields`` - field names that are never shown (e.g. ``node_id``).
"""

import sys

from dataclasses import fields as dc_fields, is_dataclass
from typing import Any, ClassVar

from .sys_args_parser import SysArgs


_RST = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_CYAN = "\033[36m"
_YELLOW = "\033[33m"
_GREEN = "\033[32m"
_MAGENTA = "\033[35m"
_BLUE = "\033[34m"


def _colors_enabled() -> bool:
    return bool(SysArgs.verbose_logs) and sys.stdout.isatty()


def _paint(text: str, *codes: str) -> str:
    if not _colors_enabled():
        return text

    return "".join(codes) + text + _RST


class TreeReprMixin:
    """Render a dataclass instance as an indented tree."""

    _tree_skip_fields: ClassVar[tuple[str, ...]] = ()

    # ------------------------- overridable hooks -------------------------

    @classmethod
    def _tree_is_node(cls, value: Any) -> bool:
        """Whether ``value`` is a tree node (rendered as a subtree)."""
        return is_dataclass(value) and not isinstance(value, type)

    @classmethod
    def _tree_format_value(cls, value: Any) -> str:
        """Stringify a scalar value, optionally colored."""
        if isinstance(value, str):
            return _paint(repr(value), _GREEN)

        if isinstance(value, (bool, int, float)):
            return _paint(repr(value), _MAGENTA)

        return repr(value)

    # ------------------------------ internals ----------------------------

    def _tree_label(self) -> str:
        """``ClassName(field=value, ...)`` for scalar fields only."""
        parts = []

        for field in dc_fields(self):
            if field.name in self._tree_skip_fields or not field.repr:
                continue

            value = getattr(self, field.name)

            if value is None or self._tree_is_node(value):
                continue

            if isinstance(value, (list, tuple)):
                continue

            parts.append(
                f"{_paint(field.name, _BLUE)}={self._tree_format_value(value)}"
            )

        name = _paint(type(self).__name__, _BOLD, _CYAN)
        return f"{name}({', '.join(parts)})" if parts else name

    @classmethod
    def _tree_child_fields(cls, node: "TreeReprMixin") -> list[tuple[str, Any]]:
        """Fields that need a branch: nested nodes and non-empty lists/tuples.

        Scalar fields are already inlined in ``_tree_label``, so they are
        skipped here to avoid showing the same value twice.
        """
        entries = []

        for field in dc_fields(node):
            if field.name in cls._tree_skip_fields or not field.repr:
                continue

            value = getattr(node, field.name)

            if value is None:
                continue

            if isinstance(value, (list, tuple)):
                value = [item for item in value if item is not None]

                if not value:
                    continue

                entries.append((field.name, value))
            elif cls._tree_is_node(value):
                entries.append((field.name, value))

        return entries

    @classmethod
    def _tree_guides(cls, prefix: str, connector: str) -> str:
        return _paint(prefix + connector, _DIM)

    @classmethod
    def _tree_render_node(
        cls, node: "TreeReprMixin", prefix: str, connector: str
    ) -> list[str]:
        lines = [f"{cls._tree_guides(prefix, connector)}{node._tree_label()}"]
        child_prefix = prefix + ("    " if connector == "└── " else "│   ")
        lines.extend(cls._tree_render_fields(node, child_prefix))
        return lines

    @classmethod
    def _tree_render_list(cls, items: list[Any], prefix: str) -> list[str]:
        lines = []

        for index, item in enumerate(items):
            last = index == len(items) - 1
            connector = "└── " if last else "├── "

            if cls._tree_is_node(item):
                lines.extend(cls._tree_render_node(item, prefix, connector))
            else:
                lines.append(
                    f"{cls._tree_guides(prefix, connector)}"
                    f"{cls._tree_format_value(item)}"
                )

        return lines

    @classmethod
    def _tree_render_fields(cls, node: "TreeReprMixin", prefix: str) -> list[str]:
        entries = cls._tree_child_fields(node)
        lines = []

        for index, (name, value) in enumerate(entries):
            last = index == len(entries) - 1
            connector = "└── " if last else "├── "
            child_prefix = prefix + ("    " if last else "│   ")

            if isinstance(value, (list, tuple)):
                lines.append(
                    f"{cls._tree_guides(prefix, connector)}{_paint(name, _BLUE)}"
                )
                lines.extend(cls._tree_render_list(list(value), child_prefix))
            else:
                lines.append(
                    f"{cls._tree_guides(prefix, connector)}"
                    f"{_paint(name, _BLUE)}: {value._tree_label()}"
                )
                lines.extend(cls._tree_render_fields(value, child_prefix))

        return lines

    # ------------------------------- public ------------------------------

    def tree_repr(self) -> str:
        lines = [self._tree_label()]
        lines.extend(self._tree_render_fields(self, ""))
        return "\n".join(lines)

    def __repr__(self):
        if SysArgs.verbose_logs:
            return self.tree_repr()

        return self._tree_label()
