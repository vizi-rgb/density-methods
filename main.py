from models.yolo.yolo import YOLOModel

path = "datasets/mall_dataset/frames"

model = YOLOModel(path)
model.run_prediction()
