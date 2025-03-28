from dataclasses import dataclass
from pathlib import Path
from pyparsing import Optional
from typing import Optional

@dataclass
class SoundInfo:
    path: str
    category: str
    filename: str
    url: Optional[str] = None # type: ignore
    
    def create_sonos_url(self, base_dir: Path, http_server_ip: str, http_server_port: int) -> None:
        sound_path = Path(self.path)
        rel_path = sound_path.relative_to(base_dir)
        url_path = str(rel_path).replace("\\", "/")
        self.url = f"http://{http_server_ip}:{http_server_port}/audio/sounds/{url_path}"