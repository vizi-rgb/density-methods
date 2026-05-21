from abc import abstractmethod, ABC
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from ultralytics.engine.results import Results

@dataclass
class Point:
    x: float
    y: float
    track_id: int = 0

@dataclass
class Prediction:
    points: list[Point] = field(default_factory=list)
    image: np.ndarray = None

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

            pred = Prediction(image=prediction.orig_img)
            if prediction.boxes.is_track:
                for box_id, box in zip(prediction.boxes.id.tolist(), prediction.boxes.xywh.tolist()):
                    x, y, w, h = box
                    pred.points += [Point(float(x), float(y) + h / 2, box_id)]
            else:
                pred.points += [Point(float(x), float(y) + h / 2) for x, y, w, h in prediction.boxes.xywh.tolist()]

            points_by_prediction.append(pred)

        return points_by_prediction

class StreamedYoloPredictionsAdapter(StreamedPredictionsAdapter):
    def to_predictions(self, raw_prediction: Results) -> Prediction:
        if raw_prediction.boxes is None or raw_prediction.boxes.xywh is None or raw_prediction.path is None:
            return Prediction()

        pred = Prediction(image=raw_prediction.orig_img)
        if raw_prediction.boxes.is_track:
            for box_id, box in zip(raw_prediction.boxes.id.tolist(), raw_prediction.boxes.xywh.tolist()):
                x, y, w, h = box
                pred.points += [Point(float(x), float(y) + h / 2, box_id)]
        else:
            pred.points += [Point(float(x), float(y) + h / 2) for x, y, w, h in raw_prediction.boxes.xywh.tolist()]
        return pred