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
    # optional: def poll(self) -> list[dict]  -- runtime commands from the device (keyboard, window close)

class Canvas:
    def __init__(self, n: int):
        self.n = n
        self.pixels: list[RGB] = [(0, 0, 0)] * n
    def set(self, i: int, c: RGB) -> None: self.pixels[i] = c
    def fill(self, c: RGB) -> None: self.pixels = [c] * self.n

def to_rgb(c: str | Sequence[int]) -> RGB:
    """'#ff8800' or [255, 136, 0] -> (255, 136, 0)"""
    if isinstance(c, str):
        h = c.lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    r, g, b = c
    return int(r), int(g), int(b)

class Theme:
    def __init__(self, colors: dict[str, RGB], gradients: dict[str, list[tuple[float, RGB]]]):
        self._colors = {"off": (0, 0, 0), **colors}
        self._gradients = {name: sorted(stops) for name, stops in gradients.items()}

    @classmethod
    def from_dict(cls, d: Mapping) -> Theme:
        """{"primary": "#ffff00", ..., "gradients": {"load": [[0, "#00ff00"], [1, "#ff0000"]]}}"""
        colors = {role: to_rgb(c) for role, c in d.items() if role != "gradients"}
        gradients = {name: [(float(pos), to_rgb(c)) for pos, c in stops]
                     for name, stops in d.get("gradients", {}).items()}
        return cls(colors, gradients)

    def color(self, role: str) -> RGB: return self._colors[role]

    def gradient(self, name: str, x: float) -> RGB:   # interpolacja po stopniach
        stops = self._gradients[name]
        if x <= stops[0][0]:
            return stops[0][1]
        for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
            if x <= p1:
                f = (x - p0) / (p1 - p0) if p1 > p0 else 1.0
                return tuple(round(a + (b - a) * f) for a, b in zip(c0, c1))
        return stops[-1][1]

class Program(ABC):
    requires: ClassVar[set[str]] = set()   # sygnały, których program potrzebuje
    done: bool = False                     # startup programs set True when finished

    # params = profile "params" merged with the program entry's own keys;
    # subclasses take what they need and swallow the rest with **_
    def __init__(self, theme: Theme, **params): self.theme = theme

    @abstractmethod
    def tick(self, t: Telemetry, dt: float, canvas: Canvas) -> None: ...
