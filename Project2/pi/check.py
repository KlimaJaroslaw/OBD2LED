"""Sanity check used by CI and by update.sh before restarting on new code:
every profile is valid and pi_config.json points at an existing profile.
Run from the OBD2LED folder:  python -m Project2.pi.check"""
import json
import sys
from pathlib import Path

from Project2.registry import load_plugins
from Project2.runtime import PROFILES, load_profile, validate


def main():
    load_plugins()
    failed = False
    for path in sorted(PROFILES.glob("*.json")):
        try:
            validate(load_profile(path))
            print(f"ok    {path.name}")
        except Exception as e:
            print(f"FAIL  {path.name}: {e}")
            failed = True
    with open(Path(__file__).resolve().parent / "pi_config.json") as f:
        config = json.load(f)
    try:
        load_profile(config["profile"])
        print(f"ok    pi_config.json -> {config['profile']}")
    except Exception as e:
        print(f"FAIL  pi_config.json: {e}")
        failed = True
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
