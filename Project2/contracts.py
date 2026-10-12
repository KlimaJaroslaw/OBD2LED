# core.py
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar, Mapping, Protocol, Sequence

RGB = tuple[int, int, int]

@dataclass(frozen=True)
class Reading:
    value: float
    time: float                      # kiedy odczytano (r.time)

@dataclass(frozen=True)
class Telemetry:
    now: float
    readings: Mapping[str, Reading]

    def get(self, name: str) -> Reading | None:
        return self.readings.get(name)

class Source(Protocol):
    def start(self, signals: set[str]) -> None: ...   # co obserwować
    def snapshot(self) -> Telemetry: ...
    def stop(self) -> None: ...

class LedDevice(Protocol):
    count: int
    def show(self, pixels: Sequence[RGB]) -> None: ...
    def close(self) -> None: ...

class Canvas:
    def __init__(self, n: int):
        self.n = n
        self.pixels: list[RGB] = [(0, 0, 0)] * n
    def set(self, i: int, c: RGB) -> None: self.pixels[i] = c
    def fill(self, c: RGB) -> None: self.pixels = [c] * self.n

class Theme:
    def __init__(self, colors: dict[str, RGB], gradients: dict[str, list[tuple[float, RGB]]]):
        self._colors, self._gradients = colors, gradients
    def color(self, role: str) -> RGB: return self._colors[role]
    def gradient(self, name: str, x: float) -> RGB: ...   # interpolacja po stopniach

class Program(ABC):
    requires: ClassVar[set[str]] = set()   # sygnały, których program potrzebuje
    def __init__(self, theme: Theme, **params): self.theme = theme
    @abstractmethod
    def tick(self, t: Telemetry, dt: float, canvas: Canvas) -> None: ...