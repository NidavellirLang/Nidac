from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class FuncArgs:
    values: list


@dataclass(slots=True)
class Type:
    value: object
    line: Any


@dataclass(slots=True)
class Body:
    body: list
