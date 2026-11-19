from dataclasses import dataclass
from functools import lru_cache

from ..irs import Child, IR


class PassContractError(TypeError):
    pass


class _Directive:
    __slots__ = ()


class Remove(_Directive):
    __slots__ = ()
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


@dataclass(frozen=True, slots=True)
class ReplaceMany(_Directive):
    nodes: tuple[IR, ...]


@lru_cache
def child_specs(cls):
    known = cls.__dataclass_fields__
    specs = tuple(
        entry if isinstance(entry, Child) else Child(entry)
        for entry in cls.__child__
    )
    unknown = [spec.name for spec in specs if spec.name not in known]
    if unknown:
        raise PassContractError(
            f"{cls.__name__}.__child__ has unknown fields: {', '.join(unknown)}"
        )
    return specs


class IRTransform:
    order = "post"
    revisit = "never"
    max_revisits = 8

    def run(self, node, ctx=None):
        self.ctx = ctx
        if self.order not in ("pre", "post"):
            raise PassContractError(
                f"{type(self).__name__} has invalid order {self.order!r}"
            )
        self.changed = False
        return self._walk(node, self.max_revisits)

    def visit(self, node):
        return node

    def _walk(self, node, budget):
        if self.order == "pre":
            original = node
            node = self._settle(node, budget)
            if not isinstance(node, IR) or node is not original:
                return node

        for spec in child_specs(type(node)):
            self._rewrite_field(node, spec)

        if self.order == "post":
            node = self._settle(node, budget)
        return node

    def _settle(self, node, budget):
        original = node
        result = self.visit(node)

        while True:
            if result is None or isinstance(result, _Directive):
                return result
            if not isinstance(result, IR):
                raise PassContractError(
                    f"{type(self).__name__}.visit returned {type(result).__name__}"
                )
            if result is original:
                return result

            self.changed = True
            if self.revisit != "node":
                return result
            if budget <= 0:
                raise PassContractError(
                    f"{type(self).__name__} did not converge on "
                    f"{type(original).__name__}"
                )

            original = result
            result = self.visit(result)
            budget -= 1

    def _flatten(self, result, out):
        if isinstance(result, Remove):
            self.changed = True
            return
        if result is None:
            raise PassContractError(
                f"{type(self).__name__} returned None in a list slot; use Remove"
            )
        if isinstance(result, ReplaceMany):
            self._validate_many(result)
            self.changed = True
            for item in result.nodes:
                if self.revisit == "node":
                    item = self._settle(item, self.max_revisits)
                self._flatten(item, out)
            return
        if not isinstance(result, IR):
            raise PassContractError(
                f"{type(self).__name__} produced {type(result).__name__}"
            )
        out.append(result)

    def _validate_many(self, directive):
        nodes = directive.nodes
        if not nodes:
            raise PassContractError(
                f"{type(self).__name__} produced an empty ReplaceMany"
            )
        for item in nodes:
            if not isinstance(item, IR):
                raise PassContractError(
                    f"{type(self).__name__}.ReplaceMany contains "
                    f"{type(item).__name__}"
                )
        if len({id(item) for item in nodes}) != len(nodes):
            raise PassContractError(
                f"{type(self).__name__}.ReplaceMany reuses the same instance"
            )

    def _rewrite_field(self, node, spec):
        value = getattr(node, spec.name)

        if isinstance(value, list):
            rewritten = []
            for item in value:
                if not isinstance(item, IR):
                    rewritten.append(item)
                    continue
                self._flatten(self._walk(item, self.max_revisits), rewritten)
            setattr(node, spec.name, rewritten)
            return

        if value is None:
            if not spec.optional:
                raise PassContractError(
                    f"{type(node).__name__}.{spec.name} is required but is None"
                )
            return
        if not isinstance(value, IR):
            raise PassContractError(
                f"{type(node).__name__}.{spec.name} is not an IR node"
            )

        result = self._walk(value, self.max_revisits)
        if result is None:
            if not spec.optional:
                raise PassContractError(
                    f"{type(self).__name__} removed required "
                    f"{type(node).__name__}.{spec.name}"
                )
            self.changed = True
            setattr(node, spec.name, None)
            return
        if isinstance(result, _Directive):
            raise PassContractError(
                f"{type(self).__name__} produced {type(result).__name__} "
                f"in singular {type(node).__name__}.{spec.name}"
            )
        setattr(node, spec.name, result)
