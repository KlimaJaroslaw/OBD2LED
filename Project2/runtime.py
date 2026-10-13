import json
import logging
import queue
import time
from pathlib import Path

from Project2.contracts import Canvas, Theme
from Project2.registry import SOURCES, DEVICES, PROGRAMS, build, load_plugins

log = logging.getLogger(__name__)

PROFILES = Path(__file__).resolve().parent / "profiles"


def load_profile(name_or_path):
    """'dev' -> profiles/dev.json; an explicit path is used as is."""
    path = Path(name_or_path)
    if not path.exists():
        path = PROFILES / (path.name if path.suffix == ".json" else f"{path.name}.json")
    with open(path) as f:
        return json.load(f)


def validate(profile):
    """Fail at startup with every problem listed, not mid-drive on the first one."""
    errors = []
    for key in ("source", "programs", "themes", "devices"):
        if key not in profile:
            errors.append(f"missing {key!r}")
    if errors:
        raise ValueError("invalid profile:\n  " + "\n  ".join(errors))

    programs, themes = profile["programs"], profile["themes"]
    if profile["source"].get("type") not in SOURCES:
        errors.append(f"source: unknown type {profile['source'].get('type')!r}, registered: {sorted(SOURCES)}")
    for name, spec in programs.items():
        if spec.get("type") not in PROGRAMS:
            errors.append(f"programs.{name}: unknown type {spec.get('type')!r}, registered: {sorted(PROGRAMS)}")
    if not themes:
        errors.append("themes: at least one theme is required")

    for i, dev in enumerate(profile["devices"]):
        where = f"devices[{i}]"
        if dev.get("type") not in DEVICES:
            errors.append(f"{where}: unknown type {dev.get('type')!r}, registered: {sorted(DEVICES)}")
        sel = dev.get("programs", {})
        refs = list(sel.get("cycle", []))
        for slot in ("startup", "initial"):
            if slot in sel:
                refs.append(sel[slot].get("program"))
                if sel[slot].get("theme") is not None and sel[slot]["theme"] not in themes:
                    errors.append(f"{where}.programs.{slot}: unknown theme {sel[slot]['theme']!r}")
        for ref in refs:
            if ref is not None and ref not in programs:
                errors.append(f"{where}.programs: unknown program {ref!r}")
    if errors:
        raise ValueError("invalid profile:\n  " + "\n  ".join(errors))


class Output:
    """One device and the program currently drawing on it."""

    def __init__(self, name, spec, profile, themes):
        self.name = name
        self.device = build(DEVICES, {k: v for k, v in spec.items() if k not in ("name", "programs")})
        self.canvas = Canvas(self.device.count)

        self._specs = profile["programs"]
        self._params = profile.get("params", {})
        self._themes = themes

        sel = spec.get("programs", {})
        startup = sel.get("startup")
        self.cycle = sel.get("cycle") or [p for p in self._specs if not startup or p != startup["program"]]
        initial = sel.get("initial", {})
        self._initial = (initial.get("program", self.cycle[0]), initial.get("theme", next(iter(themes))))

        self.program = None
        self.program_name, self.theme_name = self._initial
        self._startup_left = None  # seconds left of startup, inf = until program.done
        if startup:
            self._startup_left = startup.get("duration", float("inf"))
            self.set_program(startup["program"], startup.get("theme", self._initial[1]))
        else:
            self.set_program(*self._initial)

    @property
    def theme(self):
        return self._themes[self.theme_name]

    def set_program(self, name, theme=None):
        if theme is not None:
            self.theme_name = theme
        self.program_name = name
        try:
            self.program = build(PROGRAMS, {**self._params, **self._specs[name]}, theme=self.theme)
        except Exception:
            log.exception("%s: failed to build program %r", self.name, name)
            self.program = None
        log.info("%s: program %s, theme %s", self.name, name, self.theme_name)

    def set_theme(self, name):
        self.theme_name = name
        if self.program is not None:
            self.program.theme = self.theme  # keep program state (smoothing etc.)
        log.info("%s: theme %s", self.name, name)

    def next_program(self, step=1):
        if self._startup_left is not None:  # button during startup: skip it
            self._end_startup()
            return
        i = self.cycle.index(self.program_name) if self.program_name in self.cycle else -step
        self.set_program(self.cycle[(i + step) % len(self.cycle)])

    def next_theme(self, step=1):
        names = list(self._themes)
        self.set_theme(names[(names.index(self.theme_name) + step) % len(names)])

    def _end_startup(self):
        self._startup_left = None
        self.set_program(*self._initial)

    def render(self, telemetry, dt):
        if self._startup_left is not None:
            self._startup_left -= dt
            if self._startup_left <= 0 or self.program is None or self.program.done:
                self._end_startup()

        self.canvas.fill(self.theme.color("off"))
        if self.program is not None:
            try:
                self.program.tick(telemetry, dt, self.canvas)
            except Exception:
                # one broken program must not take down the other devices
                log.exception("%s: program %r crashed, output blanked until next switch",
                              self.name, self.program_name)
                self.program = None
                self.canvas.fill(self.theme.color("off"))
        self.device.show(self.canvas.pixels)

    def close(self):
        self.device.close()


def handle(cmd, outputs):
    """Commands: {"action": ..., "device": optional name, "program"/"theme": for set_*}.
    Returns False on "quit"."""
    action = cmd.get("action")
    if action == "quit":
        return False
    targets = [o for o in outputs if cmd.get("device") in (None, o.name)]
    if not targets:
        log.warning("command %s: no device named %r", cmd, cmd.get("device"))
    for o in targets:
        if action == "next_program":
            o.next_program(+1)
        elif action == "prev_program":
            o.next_program(-1)
        elif action == "next_theme":
            o.next_theme(+1)
        elif action == "prev_theme":
            o.next_theme(-1)
        elif action == "set_program" and cmd.get("program") in o._specs:
            o.set_program(cmd["program"])
        elif action == "set_theme" and cmd.get("theme") in o._themes:
            o.set_theme(cmd["theme"])
        else:
            log.warning("unknown or invalid command %s", cmd)
            break
    return True


def run(profile, command_queue=None):
    if command_queue is None:
        command_queue = queue.Queue()

    load_plugins()
    validate(profile)
    log.info("profile %s", profile.get("name", "?"))

    themes = {name: Theme.from_dict(t) for name, t in profile["themes"].items()}
    # one source for everything, subscribed to whatever any available program may need
    signals = set().union(*(PROGRAMS[p["type"]].requires for p in profile["programs"].values()))

    source, outputs = None, []
    try:
        for i, spec in enumerate(profile["devices"]):
            name = spec.get("name") or f"{spec['type']}{i}"
            outputs.append(Output(name, spec, profile, themes))
        source = build(SOURCES, profile["source"])
        source.start(signals)

        period = 1 / profile.get("fps", 60)
        last = time.monotonic()
        while True:
            while True:  # drain everything queued since the last frame
                try:
                    cmd = command_queue.get_nowait()
                except queue.Empty:
                    break
                if not handle(cmd, outputs):
                    return

            now = time.monotonic()
            dt, last = now - last, now

            telemetry = source.snapshot()  # same snapshot for every device in this frame
            for o in outputs:
                o.render(telemetry, dt)

            elapsed = time.monotonic() - now
            time.sleep(max(0, period - elapsed))
    finally:
        if source is not None:
            source.stop()
        for o in outputs:
            try:
                o.close()
            except Exception:
                log.exception("%s: error while closing device", o.name)
