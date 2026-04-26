from models.yolo.yolo import YOLOModel
from models.yolo_crowd.yolo_crowd import YOLOCrowdModel

path = "datasets/mall_dataset/frames/seq_000001.jpg"

model = YOLOModel(path)
res = model.run_prediction()
res[0].show()

model = YOLOCrowdModel(path)
res = model.run_prediction()
print(res)
