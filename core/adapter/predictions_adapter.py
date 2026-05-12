from dataclasses import dataclass, field
from typing import Any

from ultralytics.engine.results import Results

@dataclass
class Prediction:
    points: list[tuple[float, float]] = field(default_factory=list)
    image_path: str = None

class PredictionsAdapter:
    def to_predictions(self, raw_predictions: Any) -> list[Prediction]:
        if raw_predictions is None:
            return []

        if self._is_yolo_results_list(raw_predictions):
            return YoloPredictionsAdapter().to_predictions(raw_predictions)

        raise TypeError(
            "Unsupported predictions format. Expected list[ultralytics.engine.results.Results]."
        )

    @staticmethod
    def _is_yolo_results_list(raw_predictions):
        return isinstance(raw_predictions, list) and all(
            isinstance(prediction, Results) for prediction in raw_predictions
        )


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
