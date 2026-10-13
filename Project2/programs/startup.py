from Project2.contracts import Program
from Project2.registry import PROGRAMS, register


@register(PROGRAMS, "startup_sweep")
class StartupSweep(Program):
    """Sweeps the bar up and back down once, then reports done."""

    def __init__(self, theme, duration=2.0, gradient="load", **_):
        super().__init__(theme)
        self.duration, self.gradient, self.elapsed = duration, gradient, 0.0

    def tick(self, t, dt, canvas):
        self.elapsed += dt
        x = min(1.0, self.elapsed / self.duration)
        self.done = x >= 1.0
        lit = (1 - abs(1 - 2 * x)) * canvas.n  # 0 -> full -> 0
        for i in range(canvas.n):
            if i < lit:
                canvas.set(i, self.theme.gradient(self.gradient, i / max(1, canvas.n - 1)))
