from ultralytics import YOLO

from config.config_loader import ConfigLoader, ModelConfig
from models.base_model import BaseModel

class YOLOModel(BaseModel):
    def __init__(self, dataset_path: str):
        super().__init__(dataset_path)
        self.config = self.config_loader.load_config(ModelConfig.YOLO)
        self.model = None

    def _get_model(self):
        if self.model is None:
            self.model = YOLO(self.config["model"])
        return self.model

    def run_prediction(self):
        return self._get_model().predict(
            source=self.dataset_path,
            show=self.config.get("show", False),
            classes=self.config["classes"],
        )
