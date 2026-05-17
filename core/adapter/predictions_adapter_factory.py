from core.adapter.predictions_adapter import PredictionsAdapter, YoloPredictionsAdapter, StreamedYoloPredictionsAdapter
from models.base_model import BaseModel
from models.yolo.yolo import YOLOModel


class PredictionsAdapterFactory:

    @classmethod
    def for_model(cls, model: BaseModel) -> PredictionsAdapter:
        if isinstance(model, YOLOModel):
            return YoloPredictionsAdapter()

        raise ValueError(f"No PredictionsAdapter found for model type: {type(model)}")

class StreamedPredictionsAdapterFactory:

    @classmethod
    def for_model(cls, model: BaseModel) -> StreamedYoloPredictionsAdapter:
        if isinstance(model, YOLOModel):
            return StreamedYoloPredictionsAdapter()

        raise ValueError(f"No StreamedPredictionsAdapter found for model type: {type(model)}")
