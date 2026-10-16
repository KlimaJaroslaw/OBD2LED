"""Run on the Pi from the OBD2LED folder:  python -m Project2.pi.pi_main [pi_config.json]"""
import json
import logging
import queue
import sys
from pathlib import Path

from Project2.runtime import load_profile, run


def main(config_path=Path(__file__).resolve().parent / "pi_config.json"):
    with open(config_path) as f:
        config = json.load(f)
    logging.basicConfig(level=config.get("log_level", "INFO"),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    from gpiozero import Button

    command_queue = queue.Queue()
    buttons = []  # keep references, gpiozero stops reacting when a Button is garbage collected
    for b in config.get("buttons", []):
        cmd = {k: v for k, v in b.items() if k != "pin"}  # action (+ optional device/program/theme)
        button = Button(b["pin"], bounce_time=0.05)
        button.when_pressed = lambda cmd=cmd: command_queue.put(cmd)
        buttons.append(button)

    try:
        run(load_profile(config["profile"]), command_queue=command_queue)
    except KeyboardInterrupt:  # Ctrl+C, or systemctl stop (KillSignal=SIGINT)
        pass


if __name__ == "__main__":
    main(*sys.argv[1:])
