from typing import Any, TypeGuard

from ultralytics.engine.results import Results


class PredictionsAdapter:
    def to_points(self, raw_predictions: Any) -> list[list[tuple[float, float]]]:
        if raw_predictions is None:
            return []

        if self._is_yolo_results_list(raw_predictions):
            return YoloPredictionsAdapter().to_points(raw_predictions)

        raise TypeError(
            "Unsupported predictions format. Expected list[ultralytics.engine.results.Results]."
        )

    @staticmethod
    def _is_yolo_results_list(raw_predictions):
        return isinstance(raw_predictions, list) and all(
            isinstance(prediction, Results) for prediction in raw_predictions
        )


class YoloPredictionsAdapter(PredictionsAdapter):
    def to_points(self, raw_predictions: list[Results]) -> list[list[tuple[float, float]]]:
        points_by_prediction: list[list[tuple[float, float]]] = []

        for prediction in raw_predictions:
            if prediction.boxes is None or prediction.boxes.xywh is None:
                points_by_prediction.append([])
                continue

            points_by_prediction.append(
                [(float(x), float(y) + h / 2) for x, y, w, h in prediction.boxes.xywh.tolist()]
            )

        return points_by_prediction
