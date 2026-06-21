import cv2
import numpy as np

class CameraInfo:
    def __init__(self):
        self.camera_pts = np.array(
            [
                [293, 174],  # Example keypoint 1
                [40, 557],  # Example keypoint 2
                [1752, 524],  # Example keypoint 3]
                [1512, 149],
            ],
            dtype=np.float32
        )

        self.real_world_pts = np.array(
            [
                [0, 0],
                [0, 6],
                [15, 6],
                [15, 0]
            ],
            dtype=np.float32
        )

    def get_transformation_matrix(self):
        return cv2.getPerspectiveTransform(self.camera_pts, self.real_world_pts)

