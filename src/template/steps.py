from dataclasses import dataclass


@dataclass(frozen=True)
class BlockStep:
    block_type: str
    text: str
    index: int


@dataclass(frozen=True)
class DataSourceStep:
    name: str


@dataclass(frozen=True)
class ViewStep:
    name: str


@dataclass(frozen=True)
class PropertyStep:
    name: str
