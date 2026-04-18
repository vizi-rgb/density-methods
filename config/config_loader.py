from enum import Enum
from yaml import safe_load
from pathlib import Path

class ModelConfig(Enum):
    YOLO = "yolo"
    YOLO_CROWD = "yolo-crowd"


class ConfigLoader:
    _base_path = Path(__file__).resolve().parent
    _config_file = _base_path / "config.yaml"

    @classmethod
    def load_config(cls, config_path: ModelConfig):
        if not isinstance(config_path, ModelConfig):
            raise TypeError("config_path must be of type ModelConfig")

        with open(cls._config_file) as f:
            config = safe_load(f) or {}

        if config_path.value not in config:
            raise KeyError(f"Missing config section: '{config_path.value}'")

        return config[config_path.value]
