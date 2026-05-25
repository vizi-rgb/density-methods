from enum import Enum
from yaml import safe_load
from pathlib import Path

from project_root import PROJECT_ROOT


class ModelConfig(Enum):
    YOLO = "yolo"
    YOLO_CROWD = "yolo-crowd"


class TrackerConfig(Enum):
    BOTSORT = "botsort"


class ConfigLoader:
    _base_path = Path(__file__).resolve().parent
    _config_file = _base_path / "config.yaml"
    _tracker_config_files = {
        TrackerConfig.BOTSORT: _base_path / "botsort.yaml",
    }

    @classmethod
    def load_config(cls, config_path: ModelConfig):
        if not isinstance(config_path, ModelConfig):
            raise TypeError("config_path must be of type ModelConfig")

        with open(cls._config_file) as f:
            config = safe_load(f) or {}

        if config_path.value not in config:
            raise KeyError(f"Missing config section: '{config_path.value}'")

        ret = config[config_path.value]
        if "weights" in ret:
            ret["weights"] = PROJECT_ROOT / ret["weights"]

        return ret

    @classmethod
    def load_tracker_config(cls, config_path: TrackerConfig):
        if not isinstance(config_path, TrackerConfig):
            raise TypeError("config_path must be of type TrackerConfig")
        if config_path not in cls._tracker_config_files:
            raise KeyError(f"Missing tracker config: '{config_path.value}'")

        config_file = cls._tracker_config_files[config_path]
        if not config_file.exists():
            raise FileNotFoundError(f"Tracker config file not found: {config_file}")

        with open(config_file) as f:
            config = safe_load(f) or {}

        if not config:
            raise ValueError(f"Tracker config is empty: {config_file}")

        return config
