import math

from Project2.contracts import Program
from Project2.registry import PROGRAMS, register


class SignalBar(Program):
    """Fills the strip proportionally to one signal between lo and hi, colored by a gradient."""
    signal = ""

    def __init__(self, theme, lo, hi, smoothing_tau=0.08, gradient="load", stale_after=1.0, **_):
        super().__init__(theme)
        self.lo, self.hi, self.tau = lo, hi, smoothing_tau
        self.gradient, self.stale_after = gradient, stale_after
        self.level = 0.0

    def tick(self, t, dt, canvas):
        r = t.get(self.signal)
        fresh = r is not None and t.now - r.time <= self.stale_after
        target = min(1.0, max(0.0, (r.value - self.lo) / (self.hi - self.lo))) if fresh else 0.0
        self.level += (target - self.level) * (1 - math.exp(-dt / self.tau) if self.tau > 0 else 1)
        lit = self.level * canvas.n
        for i in range(canvas.n):
            if i < lit:
                canvas.set(i, self.theme.gradient(self.gradient, i / max(1, canvas.n - 1)))


@register(PROGRAMS, "rpm_bar")
class RpmBar(SignalBar):
    signal = "rpm"
    requires = {"rpm"}

    def __init__(self, theme, min_rpm=800, max_rpm=6500, **params):
        super().__init__(theme, lo=min_rpm, hi=max_rpm, **params)


@register(PROGRAMS, "speed_bar")
class SpeedBar(SignalBar):
    signal = "speed"
    requires = {"speed"}

    def __init__(self, theme, min_speed=0, max_speed=140, **params):
        super().__init__(theme, lo=min_speed, hi=max_speed, **params)
