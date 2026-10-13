import sys

from Project2.registry import DEVICES, register


@register(DEVICES, "console")
class ConsoleDevice:
    """Draws the strip as one line of 24-bit colored blocks, redrawn in place.
    Only one console device per terminal makes sense (they share the line)."""

    def __init__(self, count=30, label="", stream=None):
        self.count, self.label = count, label
        self._out = stream or sys.stdout
        self._last = None

    def show(self, pixels):
        if pixels == self._last:
            return
        self._last = list(pixels)
        bar = "".join(f"\x1b[38;2;{r};{g};{b}m█" for r, g, b in pixels)
        self._out.write(f"\r{self.label}{bar}\x1b[0m")
        self._out.flush()

    def close(self):
        self._out.write("\n")
        self._out.flush()
