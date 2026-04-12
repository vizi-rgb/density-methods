from enum import Enum
from yaml import safe_load
from pathlib import Path

class ModelConfig(Enum):
    YOLO = "yolo.yaml"


class ConfigLoader:
    _base_path = Path(__file__).resolve().parent / "yaml"

    @classmethod
    def load_config(cls, config_path: ModelConfig):
        if not isinstance(config_path, ModelConfig):
            raise TypeError("config_path must be of type ModelConfig")

        with open(cls._base_path / config_path.value) as f:
            return safe_load(f)
