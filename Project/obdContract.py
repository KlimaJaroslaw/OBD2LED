from dataclasses import dataclass

@dataclass
class OBDContract:
    rpm_available: bool = True
    speed_available: bool = True
    rpm: int = 0
    speed: int = 0    