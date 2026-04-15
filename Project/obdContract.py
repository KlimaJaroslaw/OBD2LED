from dataclasses import dataclass

@dataclass
class OBDContract:
    rpm_supported: bool = True
    rpm_timestamp: float = 0.0
    rpm: int = 0
    speed_supported: bool = True
    speed_timestamp: float = 0.0
    speed: int = 0    