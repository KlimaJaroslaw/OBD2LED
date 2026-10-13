"""Dev runner, from the OBD2LED folder:  python -m Project2.main [profile]   (default: dev)

Type a command + Enter while it runs:
  n / p   next / previous program      t / T   next / previous theme
  q       quit
Optionally followed by a device name, e.g. "n console".
"""
import logging
import queue
import sys
import threading

from Project2.runtime import load_profile, run

KEYS = {"n": "next_program", "p": "prev_program", "t": "next_theme", "T": "prev_theme", "q": "quit"}


def read_commands(command_queue):
    for line in sys.stdin:
        key, *device = line.split()
        if key in KEYS:
            command_queue.put({"action": KEYS[key], "device": device[0] if device else None})
    command_queue.put({"action": "quit"})


def main(profile="dev"):
    logging.basicConfig(level=logging.INFO, format="\n%(levelname)s %(name)s: %(message)s")
    command_queue = queue.Queue()
    threading.Thread(target=read_commands, args=(command_queue,), daemon=True).start()
    try:
        run(load_profile(profile), command_queue=command_queue)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main(*sys.argv[1:])
