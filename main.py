from pathlib import Path

import cv2

from core.adapter.predictions import PredictionsAdapter
from models.yolo.yolo import YOLOModel
from project_root import PROJECT_ROOT

path = "data/datasets/mall_dataset/frames/seq_000001.jpg"


def _resolve_path(image_path: str) -> Path:
    path_obj = Path(image_path)
    if path_obj.is_absolute():
        return path_obj
    return PROJECT_ROOT / path_obj


def main() -> None:
    model = YOLOModel(path)
    raw_predictions = model.run_prediction(show=False)
    points_by_prediction = PredictionsAdapter().to_points(raw_predictions)

    if not points_by_prediction:
        raise RuntimeError("No predictions were produced.")

    points = points_by_prediction[0]
    image_path = _resolve_path(path)
    image = cv2.imread(str(image_path))
    if image is None:
        raise FileNotFoundError(f"Could not load image from path: {image_path}")

    for x, y in points:
        cv2.circle(
            image,
            (int(round(x)), int(round(y))),
            4,
            (0, 0, 255),
            thickness=-1,
        )

    cv2.imshow("YOLO points", image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
