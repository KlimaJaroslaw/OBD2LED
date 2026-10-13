import bisect
import logging
import threading
import time
from pathlib import Path

from Project2.contracts import Reading, Telemetry
from Project2.registry import SOURCES, register

log = logging.getLogger(__name__)

RESOURCES = Path(__file__).resolve().parent.parent / "resources"


@register(SOURCES, "replay")
class ReplaySource:
    """Plays back a recorded drive (pickled pandas DataFrame) in real time.

    Recording format: a `timestamp` column (epoch seconds) plus one column per
    signal, named like the live source's signals ("rpm", "speed", ...).

    Telemetry clock is the recording's own clock: `now` is the virtual playback
    time and each Reading.time is the timestamp of the row it came from, so
    `now - reading.time` (staleness) behaves the same as with the live source.
    """

    def __init__(self, file="obd_readings.pkl", speed=1.0, loop=True, interpolate=False):
        import pandas as pd  # only needed for replay; keeps the Pi free of pandas

        path = Path(file)
        if not path.is_absolute() and not path.exists():
            path = RESOURCES / path
        df = pd.read_pickle(path).sort_values("timestamp")

        self.speed, self.loop, self.interpolate = float(speed), loop, interpolate
        self._times: list[float] = df["timestamp"].astype(float).tolist()
        self._columns = {c: df[c].astype(float).tolist() for c in df.columns if c != "timestamp"}

        t = self._times
        step = (t[-1] - t[0]) / (len(t) - 1) if len(t) > 1 else 0.0
        self._t0 = t[0]
        self._period = (t[-1] - t[0]) + step  # one sample gap before wrapping around
        self._signals: set[str] = set()
        self._started_at: float | None = None
        self._lock = threading.Lock()
        log.info("replay %s: %d rows, %.1fs, signals %s",
                 path.name, len(t), self._period, sorted(self._columns))

    def start(self, signals):
        missing = set(signals) - self._columns.keys()
        if missing:
            log.warning("replay: signals not in recording: %s", sorted(missing))
        with self._lock:
            self._signals = set(signals) & self._columns.keys()
            self._started_at = time.monotonic()

    def snapshot(self) -> Telemetry:
        with self._lock:
            if self._started_at is None:
                return Telemetry(now=self._t0, readings={})
            offset = (time.monotonic() - self._started_at) * self.speed
            signals = self._signals

        if self.loop and self._period > 0:
            offset %= self._period
        now = self._t0 + offset

        i = bisect.bisect_right(self._times, now) - 1  # last row at or before `now`
        i = max(0, min(i, len(self._times) - 1))
        readings = {}
        for name in signals:
            value = self._value(name, i, now)
            if value == value:  # skip NaN (signal not sampled in this row)
                readings[name] = Reading(value=value, time=self._times[i])
        return Telemetry(now=now, readings=readings)

    def _value(self, name, i, now):
        col = self._columns[name]
        if not self.interpolate or i + 1 >= len(col):
            return col[i]
        t_a, t_b = self._times[i], self._times[i + 1]
        frac = (now - t_a) / (t_b - t_a) if t_b > t_a else 0.0
        return col[i] + (col[i + 1] - col[i]) * min(1.0, max(0.0, frac))

    def stop(self):
        with self._lock:
            self._started_at = None
