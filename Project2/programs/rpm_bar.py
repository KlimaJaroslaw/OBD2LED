from Project2.contracts import Program
from Project2.registry import PROGRAMS


@register(PROGRAMS, "rpm_bar")
class RpmBar(Program):
    requires = {"rpm"}

    def __init__(self, theme, rpm_min=800, rpm_max=6500, smoothing_tau=0.08):
        super().__init__(theme)
        self.lo, self.hi, self.tau, self.level = rpm_min, rpm_max, smoothing_tau, 0.0

    def tick(self, t, dt, canvas):
        r = t.get("rpm")
        target = 0.0 if r is None else min(1, max(0, (r.value - self.lo) / (self.hi - self.lo)))
        self.level += (target - self.level) * (1 - math.exp(-dt / self.tau))
        lit = self.level * canvas.n
        for i in range(canvas.n):
            canvas.set(i, self.theme.gradient("load", i / (canvas.n - 1))
                          if i < lit else self.theme.color("off"))