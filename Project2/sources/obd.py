import logging
import threading
import time

from Project2.contracts import Reading, Telemetry
from Project2.registry import SOURCES, register

log = logging.getLogger(__name__)


@register(SOURCES, "obd")
class ObdSource:
    """Live telemetry from an ELM327 adapter via python-OBD (obd.Async).

    Signal names are lowercase python-OBD command names: "rpm" -> obd.commands.RPM,
    "speed" -> SPEED, "coolant_temp" -> COOLANT_TEMP, "throttle_pos" -> THROTTLE_POS...
    Values are stored as plain floats in python-OBD's default units (rpm, km/h, °C, %).

    A background supervisor thread connects, keeps retrying until the car answers
    (adapter plugged in, ignition on), and reconnects after a drop. Readings that
    stop updating keep their old `time`, so programs can detect stale data via
    `t.now - reading.time`. Both clocks are wall time (time.time()), as in python-OBD.
    """

    def __init__(self, port=None, baudrate=None, protocol=None, fast=True,
                 timeout=0.1, delay_cmds=0.0, retry_interval=3.0):
        self.port, self.baudrate, self.protocol = port, baudrate, protocol
        self.fast, self.timeout, self.delay_cmds = fast, timeout, delay_cmds
        self.retry_interval = retry_interval

        self._signals: set[str] = set()
        self._latest: dict[str, Reading] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._conn = None
        self.status = "stopped"  # for diagnostics: stopped / connecting / connected

    # --- Source protocol ---------------------------------------------------------

    def start(self, signals):
        self.stop()
        self._signals = set(signals)
        self._stop.clear()
        self._thread = threading.Thread(target=self._supervise, name="obd-source", daemon=True)
        self._thread.start()

    def snapshot(self) -> Telemetry:
        with self._lock:
            readings = dict(self._latest)
        return Telemetry(now=time.time(), readings=readings)

    def stop(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
        self._close()
        with self._lock:
            self._latest.clear()
        self.status = "stopped"

    # --- connection handling -----------------------------------------------------

    def _supervise(self):
        import obd  # imported lazily so replay-only setups don't need python-OBD

        commands = {}
        for name in self._signals:
            if obd.commands.has_name(name.upper()):
                commands[name] = obd.commands[name.upper()]
            else:
                log.warning("obd: unknown signal %r (no python-OBD command %s)", name, name.upper())

        while not self._stop.is_set():
            if self._conn is None or not self._conn.running:
                self._close()
                self.status = "connecting"
                self._connect(obd, commands)
            self._stop.wait(self.retry_interval if self._conn is None else 0.5)

    def _connect(self, obd, commands):
        try:
            conn = obd.Async(self.port, self.baudrate, self.protocol, fast=self.fast,
                             timeout=self.timeout, delay_cmds=self.delay_cmds)
        except Exception:
            log.exception("obd: failed to open adapter")
            return

        if conn.status() != obd.OBDStatus.CAR_CONNECTED:
            log.info("obd: not connected to car (%s), retrying in %gs", conn.status(), self.retry_interval)
            conn.close()
            return

        watched = 0
        for name, cmd in commands.items():
            if conn.supports(cmd):
                conn.watch(cmd, callback=self._make_callback(name))
                watched += 1
            else:
                log.warning("obd: car does not support %s", cmd.name)
        conn.start()
        self._conn = conn
        self.status = "connected"
        log.info("obd: connected on %s (%s), watching %d signals",
                 conn.port_name(), conn.protocol_name(), watched)

    def _make_callback(self, name):
        def on_response(r):
            if r.is_null():
                return
            value = getattr(r.value, "magnitude", r.value)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                with self._lock:
                    self._latest[name] = Reading(value=float(value), time=r.time)
        return on_response

    def _close(self):
        conn, self._conn = self._conn, None
        if conn is not None:
            try:
                conn.stop()
                conn.close()
            except Exception:
                log.exception("obd: error while closing connection")
