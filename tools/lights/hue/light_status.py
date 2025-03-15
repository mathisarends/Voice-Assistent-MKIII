from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple

@dataclass
class LightStatus:
    device_id: str
    name: str
    is_on: bool
    brightness: int
    color_rgb: Tuple[int, int, int]
    reachable: bool = True
    device_type: str = ""
    model_id: str = ""
    max_lumen: int = 0
    min_dim_level: int = 0
    
    def __str__(self) -> str:
        """Menschenlesbare Darstellung des Status."""
        status = "AN" if self.is_on else "AUS"
        r, g, b = self.color_rgb
        return (
            f"{self.name} ({self.device_id}, {self.device_type}): {status}, "
            f"Helligkeit: {self.brightness}%, "
            f"Farbe: RGB({r},{g},{b})"
        )
    
    def as_dict(self) -> Dict[str, Any]:
        """Konvertiert den Status in ein Dictionary."""
        return {
            "device_id": self.device_id,
            "name": self.name,
            "is_on": self.is_on,
            "brightness": self.brightness,
            "color_rgb": self.color_rgb,
            "reachable": self.reachable,
            "device_type": self.device_type,
            "model_id": self.model_id,
            "max_lumen": self.max_lumen,
            "min_dim_level": self.min_dim_level
        }
