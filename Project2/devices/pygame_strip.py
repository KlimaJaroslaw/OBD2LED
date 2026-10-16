import logging

from Project2.registry import DEVICES, register

log = logging.getLogger(__name__)

BACKGROUND, LED_RIM, TEXT, TEXT_SELECTED = (24, 24, 28), (55, 55, 62), (150, 150, 160), (255, 255, 255)
MARGIN, LABEL_WIDTH, HEADER = 16, 110, 34
HELP = "n/p program   t/T theme   1-9 select device, 0 all   q quit"
KEYS = {"n": "next_program", "p": "prev_program", "t": "next_theme", "T": "prev_theme"}


class _Window:
    """pygame has a single display, so all pygame devices share one window, one row each.
    Keyboard events become runtime commands, aimed at the selected row (or all rows)."""

    _instance = None

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        import pygame
        self.pg = pygame
        pygame.init()
        pygame.display.set_caption("OBD2LED")
        self.font = pygame.font.Font(None, 22)
        self.rows: list["PygameDevice"] = []
        self.selected = 0  # 0 = all devices, n = rows[n - 1]
        self.screen = None

    def add(self, dev):
        self.rows.append(dev)
        self._layout()

    def remove(self, dev):
        self.rows.remove(dev)
        if not self.rows:
            self.pg.quit()
            _Window._instance = None
        else:
            self._layout()

    def _layout(self):
        y = HEADER
        for row in self.rows:
            row.top = y
            y += row.height
        width = max(r.width for r in self.rows) + LABEL_WIDTH + 2 * MARGIN
        self.screen = self.pg.display.set_mode((max(width, 520), y + MARGIN))
        self.redraw()

    def redraw(self):
        self.screen.fill(BACKGROUND)
        self.screen.blit(self.font.render(HELP, True, TEXT), (MARGIN, 10))
        for i, row in enumerate(self.rows, start=1):
            color = TEXT_SELECTED if self.selected in (0, i) else TEXT
            self.screen.blit(self.font.render(row.label, True, color), (MARGIN, row.top + 4))
            row.draw()
        self.pg.display.flip()

    def pump(self):
        """Turn pending window events into commands, queued on the device they target."""
        pg = self.pg
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.rows[0].pending.append({"action": "quit"})
            elif event.type == pg.KEYDOWN:
                key = event.unicode
                if event.key == pg.K_ESCAPE or key == "q":
                    self.rows[0].pending.append({"action": "quit"})
                elif key.isdigit() and int(key) <= len(self.rows):
                    self.selected = int(key)
                    self.redraw()
                elif key in KEYS:
                    cmd = {"action": KEYS[key], "device": None}
                    target = self.rows[0]
                    if self.selected:
                        target, cmd["device"] = self.rows[self.selected - 1], "self"
                    target.pending.append(cmd)


@register(DEVICES, "pygame")
class PygameDevice:
    """Simulated LED strip in a pygame window, for development on a desktop.

    columns wraps a long strip into several lines. Other keys (data_pin, brightness...)
    are ignored, so a ws281x device entry can be switched to "pygame" by changing its type.
    """

    def __init__(self, count=30, label=None, size=22, gap=6, columns=None, **ignored):
        self.count, self.size, self.gap = count, size, gap
        self.columns = columns or count
        self.label = label or f"strip {count}"
        lines = -(-count // self.columns)
        self.width = self.columns * (size + gap)
        self.height = lines * (size + gap) + gap
        self.top = 0
        self.pending: list[dict] = []
        self._pixels = [(0, 0, 0)] * count
        self._window = _Window.get()
        self._window.add(self)

    def _center(self, i):
        step = self.size + self.gap
        x = MARGIN + LABEL_WIDTH + (i % self.columns) * step + self.size // 2
        y = self.top + (i // self.columns) * step + self.size // 2 + self.gap // 2
        return x, y

    def draw(self):
        pg, screen, r = self._window.pg, self._window.screen, self.size // 2
        for i, color in enumerate(self._pixels):
            center = self._center(i)
            pg.draw.circle(screen, LED_RIM, center, r + 1)
            pg.draw.circle(screen, color, center, r - 1)

    def show(self, pixels):
        if pixels != self._pixels:
            self._pixels = list(pixels)
            self.draw()
            w = self._window
            w.pg.display.update((MARGIN + LABEL_WIDTH, self.top, self.width, self.height))

    def poll(self):
        """Optional device hook: commands produced by the device (keyboard, window close)."""
        self._window.pump()
        cmds, self.pending = self.pending, []
        return cmds

    def close(self):
        self._window.remove(self)
