import logging

from ultralytics import YOLO
from ultralytics.engine.results import Results

from config.config_loader import ModelConfig
from models.base_model import BaseModel
from ultralytics.utils import set_logging

logger = logging.getLogger(__name__)


class YOLOModel(BaseModel):
    def __init__(self, dataset_path: str):
        super().__init__(dataset_path)
        self.config = self.config_loader.load_config(ModelConfig.YOLO)
        self.model = None
        if self.config.get("logging", False):
            set_logging()
            logging.basicConfig(level=logging.INFO, format="%(message)s")
            logger.setLevel(logging.INFO)
            logger.info("YOLO logging enabled")

    def _get_model(self):
        if self.model is None:
            logger.info("Loading YOLO model: %s", self.config["weights"])
            self.model = YOLO(self.config["weights"])
        return self.model

    def run_prediction(self, show: bool = None, stream: bool = False) -> list[Results]:
        logger.info("Running YOLO prediction on source: %s", self.dataset_path)
        return self._get_model().predict(
            source=self.dataset_path,
            show=self.config.get("show", False) if show is None else show,
            classes=self.config["classes"],
            device=self.config["device"],
            conf=self.config["conf"],
            iou=self.config["iou"],
            stream=stream
        )

    def run_tracking(self, show: bool = None, stream: bool = False):
        logger.info("Running YOLO tracking on source: %s", self.dataset_path)
        return self._get_model().track(
            source=self.dataset_path,
            show=self.config.get("show", False) if show is None else show,
            classes=self.config["classes"],
            device=self.config["device"],
            conf=self.config["conf"],
            iou=self.config["iou"],
            stream=stream,
            persist=True
        )
