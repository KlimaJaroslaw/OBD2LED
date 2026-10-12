import queue
import time

from Project2.contracts import Canvas
from Project2.registry import SOURCES, DEVICES, PROGRAMS


def run(initial_profile, command_queue=None):
    # Jeśli kolejka nie została przekazana, twórzmy pustą (np. do testów bez sterowania)
    if command_queue is None:
        command_queue = queue.Queue()

    profile = dict(initial_profile)

    theme = load_theme(profile["theme"])
    source = build(SOURCES, profile["source"])
    device = build(DEVICES, profile["device"])
    program = build(PROGRAMS, profile["program"], theme=theme)

    canvas = Canvas(device.count)
    source.start(program.requires)

    period = 1 / profile.get("fps", 60)
    last = time.monotonic()
    programs_list = list(PROGRAMS.keys())

    try:
        while True:
            # --- OBSŁUGA ZDARZEŃ Z KOLEJKI ---
            try:
                cmd = command_queue.get_nowait()
                action = cmd.get("action")

                if action == "next_program":
                    curr_idx = programs_list.index(profile["program"])
                    profile["program"] = programs_list[(curr_idx + 1) % len(programs_list)]

                    source.stop()
                    program = build(PROGRAMS, profile["program"], theme=theme)
                    source.start(profile["program"] and program.requires)  # lub program.requires

                elif action == "change_theme":
                    profile["theme"] = cmd["theme"]
                    theme = load_theme(profile["theme"])
                    program = build(PROGRAMS, profile["program"], theme=theme)

            except queue.Empty:
                pass

            # --- STANDARDOWA PĘTLA ---
            now = time.monotonic()
            dt, last = now - last, now

            canvas.fill(theme.color("off"))
            program.tick(source.snapshot(), dt, canvas)
            device.show(canvas.pixels)

            elapsed = time.monotonic() - now
            time.sleep(max(0, period - elapsed))

    finally:
        source.stop()
        device.close()