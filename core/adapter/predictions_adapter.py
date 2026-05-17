from abc import abstractmethod, ABC
from dataclasses import dataclass, field
from typing import Any

from ultralytics.engine.results import Results

from models.base_model import BaseModel
from models.yolo.yolo import YOLOModel


@dataclass
class Prediction:
    points: list[tuple[float, float]] = field(default_factory=list)
    image_path: str = None

class PredictionsAdapter(ABC):

    @abstractmethod
    def to_predictions(self, raw_predictions: Any) -> list[Prediction]:
        pass

class StreamedPredictionsAdapter(ABC):

    @abstractmethod
    def to_predictions(self, raw_prediction: Any) -> Prediction:
        pass

class YoloPredictionsAdapter(PredictionsAdapter):
    def to_predictions(self, raw_predictions: list[Results]) -> list[Prediction]:
        points_by_prediction: list[Prediction] = []

        for prediction in raw_predictions:
            if prediction.boxes is None or prediction.boxes.xywh is None:
                points_by_prediction.append(Prediction())
                continue

            pred = Prediction(image_path=prediction.path)
            pred.points += [(float(x), float(y) + h / 2) for x, y, w, h in prediction.boxes.xywh.tolist()]
            points_by_prediction.append(pred)

        return points_by_prediction

class StreamedYoloPredictionsAdapter(StreamedPredictionsAdapter):
    def to_predictions(self, raw_prediction: Results) -> Prediction:
        if raw_prediction.boxes is None or raw_prediction.boxes.xywh is None or raw_prediction.path is None:
            return Prediction()

        pred = Prediction(image_path=raw_prediction.path)
        pred.points += [(float(x), float(y) + h / 2) for x, y, w, h in raw_prediction.boxes.xywh.tolist()]
        return pred