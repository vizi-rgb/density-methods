import importlib.util
import sys
import types
from pathlib import Path

import cv2
import torch
import torch.backends.cudnn as cudnn
import numpy

from config.config_loader import ModelConfig
from models.base_model import BaseModel


class YOLOCrowdModel(BaseModel):
    _internal_ready = False

    def __init__(self, dataset_path: str):
        super().__init__(dataset_path)
        self.config = self.config_loader.load_config(ModelConfig.YOLO_CROWD)
        self.model = None
        self.runtime = None
        self._runtime_signature = None

    @classmethod
    def _load_module_from_path(cls, module_name: str, module_path: Path):
        loaded = sys.modules.get(module_name)
        if loaded is not None and Path(getattr(loaded, "__file__", "")) == module_path:
            return loaded

        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise ImportError(
                f"Cannot load module '{module_name}' from '{module_path}'"
            )
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    @classmethod
    def _ensure_internal_imports(cls):
        if cls._internal_ready:
            return

        internal_root = Path(__file__).resolve().parent / "internal"
        if str(internal_root) not in sys.path:
            sys.path.insert(0, str(internal_root))

        cls._load_module_from_path(
            "models.common", internal_root / "models" / "common.py"
        )
        experimental = cls._load_module_from_path(
            "models.experimental", internal_root / "models" / "experimental.py"
        )
        cls._load_module_from_path("models.yolo", internal_root / "models" / "yolo.py")

        from utils.datasets import LoadImages, LoadStreams
        from utils.general import (
            check_img_size,
            check_imshow,
            increment_path,
            non_max_suppression,
            scale_coords,
            set_logging,
            xyxy2xywh,
        )
        from utils.plots import plot_one_box
        from utils.torch_utils import select_device, time_synchronized

        cls._attempt_load = staticmethod(experimental.attempt_load)
        cls._LoadImages = LoadImages
        cls._LoadStreams = LoadStreams
        cls._check_img_size = staticmethod(check_img_size)
        cls._check_imshow = staticmethod(check_imshow)
        cls._increment_path = staticmethod(increment_path)
        cls._non_max_suppression = staticmethod(non_max_suppression)
        cls._scale_coords = staticmethod(scale_coords)
        cls._set_logging = staticmethod(set_logging)
        cls._xyxy2xywh = staticmethod(xyxy2xywh)
        cls._plot_one_box = staticmethod(plot_one_box)
        cls._select_device = staticmethod(select_device)
        cls._time_synchronized = staticmethod(time_synchronized)
        cls._internal_ready = True

    def _build_options(self):
        weights = self.config.get("weights", self.config.get("model"))
        if not weights:
            raise KeyError("yolo-crowd config requires 'model' or 'weights'")

        source = self.dataset_path
        if not source:
            raise ValueError("Dataset path is required for YOLO-CROWD inference")

        return {
            "weights": weights,
            "source": source,
            "img_size": self.config.get("img_size", 640),
            "conf_thres": self.config.get("conf", self.config.get("conf_thres", 0.25)),
            "iou_thres": self.config.get("iou", self.config.get("iou_thres", 0.45)),
            "device": self.config.get("device", ""),
            "view_img": self.config.get("show", self.config.get("view_img", False)),
            "save_txt": self.config.get("save_txt", False),
            "save_conf": self.config.get("save_conf", False),
            "nosave": self.config.get("nosave", True),
            "classes": self.config.get("classes"),
            "agnostic_nms": self.config.get("agnostic_nms", False),
            "augment": self.config.get("augment", False),
            "project": self.config.get("project", "runs/detect"),
            "name": self.config.get("name", "exp"),
            "exist_ok": self.config.get("exist_ok", False),
            "line_thickness": self.config.get("line_thickness", 3),
            "count_overlay": self.config.get("count_overlay", False),
        }

    @staticmethod
    def _register_torch_safe_globals():
        if not hasattr(torch, "serialization") or not hasattr(
            torch.serialization, "add_safe_globals"
        ):
            return

        safe_globals = [
            (numpy._core.multiarray._reconstruct, "numpy.core.multiarray._reconstruct"),
            numpy.ndarray,
            numpy.dtype,
        ]
        for name in dir(numpy.dtypes):
            obj = getattr(numpy.dtypes, name)
            if isinstance(obj, type):
                safe_globals.append(obj)

        for module_name in ("models.yolo", "models.common", "models.experimental"):
            module = sys.modules.get(module_name)
            if module is None:
                continue
            for value in vars(module).values():
                if isinstance(value, type) and getattr(
                    value, "__module__", ""
                ).startswith(module_name):
                    safe_globals.append(value)

        for value in vars(torch.nn).values():
            if isinstance(value, type):
                safe_globals.append(value)

        for submodule in vars(torch.nn.modules).values():
            if isinstance(submodule, types.ModuleType):
                for value in vars(submodule).values():
                    if isinstance(value, type):
                        safe_globals.append(value)

        torch.serialization.add_safe_globals(safe_globals)

    def _get_model(self):
        self._ensure_internal_imports()
        self._register_torch_safe_globals()
        options = self._build_options()
        signature = (
            str(options["weights"]),
            str(options["device"]),
            int(options["img_size"]),
        )

        if self.runtime is None or self._runtime_signature != signature:
            self._set_logging()
            device = self._select_device(options["device"])
            model = self._attempt_load(options["weights"], map_location=device)
            stride = int(model.stride.max())
            img_size = self._check_img_size(int(options["img_size"]), s=stride)
            half = device.type != "cpu"
            if half:
                model.half()

            if device.type != "cpu":
                model(
                    torch.zeros(1, 3, img_size, img_size)
                    .to(device)
                    .type_as(next(model.parameters()))
                )

            self.model = model
            self.runtime = {
                "device": device,
                "stride": stride,
                "img_size": img_size,
                "half": half,
                "names": model.module.names
                if hasattr(model, "module")
                else model.names,
            }
            self._runtime_signature = signature

        return self.model

    def run_prediction(self, show: bool = None, stream: bool = False) -> list[dict]:
        options = self._build_options()
        model = self._get_model()
        runtime = self.runtime

        source = str(options["source"])
        save_img = (not options["nosave"]) and (not source.endswith(".txt"))
        webcam = (
            source.isnumeric()
            or source.endswith(".txt")
            or source.lower().startswith(("rtsp://", "rtmp://", "http://", "https://"))
        )

        save_txt = bool(options["save_txt"])
        save_dir = None
        if save_txt or save_img:
            save_dir = Path(
                self._increment_path(
                    Path(options["project"]) / options["name"],
                    exist_ok=options["exist_ok"],
                )
            )
            (save_dir / "labels" if save_txt else save_dir).mkdir(
                parents=True, exist_ok=True
            )

        view_img = bool(options["view_img"])
        if webcam:
            view_img = self._check_imshow() and view_img
            cudnn.benchmark = True
            dataset = self._LoadStreams(
                source, img_size=runtime["img_size"], stride=runtime["stride"]
            )
        else:
            dataset = self._LoadImages(
                source, img_size=runtime["img_size"], stride=runtime["stride"]
            )

        device = runtime["device"]
        half = runtime["half"]
        names = runtime["names"]
        vid_path, vid_writer = None, None
        predictions = []

        for path, img, im0s, vid_cap in dataset:
            img = torch.from_numpy(img).to(device)
            img = img.half() if half else img.float()
            img /= 255.0
            if img.ndimension() == 3:
                img = img.unsqueeze(0)

            inference_start = self._time_synchronized()
            pred = model(img, augment=options["augment"])[0]
            pred = self._non_max_suppression(
                pred,
                options["conf_thres"],
                options["iou_thres"],
                classes=options["classes"],
                agnostic=options["agnostic_nms"],
            )
            _ = self._time_synchronized() - inference_start

            for i, det in enumerate(pred):
                if webcam:
                    p, im0, frame = path[i], im0s[i].copy(), dataset.count
                else:
                    p, im0, frame = path, im0s, getattr(dataset, "frame", 0)

                p = Path(p)
                class_counts = {}

                if len(det):
                    det[:, :4] = self._scale_coords(
                        img.shape[2:], det[:, :4], im0.shape
                    ).round()
                    for c in det[:, -1].unique():
                        class_counts[int(c)] = int((det[:, -1] == c).sum().item())

                    gn = torch.tensor(im0.shape)[[1, 0, 1, 0]]
                    for *xyxy, conf, cls in reversed(det):
                        if save_txt and save_dir is not None:
                            txt_path = str(save_dir / "labels" / p.stem) + (
                                "" if dataset.mode == "image" else f"_{frame}"
                            )
                            xywh = (
                                (self._xyxy2xywh(torch.tensor(xyxy).view(1, 4)) / gn)
                                .view(-1)
                                .tolist()
                            )
                            line = (
                                (cls, *xywh, conf)
                                if options["save_conf"]
                                else (cls, *xywh)
                            )
                            with open(txt_path + ".txt", "a") as file:
                                file.write(("%g " * len(line)).rstrip() % line + "\n")

                        if save_img or view_img:
                            self._plot_one_box(
                                xyxy,
                                im0,
                                label=None,
                                color=(0, 255, 0),
                                line_thickness=int(options["line_thickness"]),
                            )

                people_count = class_counts.get(0, int(len(det)))
                if options["count_overlay"] and (save_img or view_img):
                    cv2.putText(
                        im0,
                        f"Number of people={people_count}",
                        (30, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (0, 255, 0),
                        2,
                    )

                if view_img:
                    cv2.imshow(str(p), im0)
                    cv2.waitKey(1)

                if save_img and save_dir is not None:
                    save_path = str(save_dir / p.name)
                    if dataset.mode == "image":
                        cv2.imwrite(save_path, im0)
                    else:
                        if vid_path != save_path:
                            vid_path = save_path
                            if isinstance(vid_writer, cv2.VideoWriter):
                                vid_writer.release()
                            if vid_cap:
                                fps = vid_cap.get(cv2.CAP_PROP_FPS)
                                w = int(vid_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                                h = int(vid_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                            else:
                                fps, w, h = 30, im0.shape[1], im0.shape[0]
                                save_path += ".mp4"
                            vid_writer = cv2.VideoWriter(
                                save_path,
                                cv2.VideoWriter_fourcc(*"mp4v"),
                                fps,
                                (w, h),
                            )
                        vid_writer.write(im0)

                predictions.append(
                    {
                        "path": str(p),
                        "detections": det.detach().cpu(),
                        "count": people_count,
                        "class_counts": class_counts,
                    }
                )

        if view_img:
            cv2.destroyAllWindows()

        return predictions

    def run_tracking(self, show: bool = None, stream: bool = False) -> list[dict]:
        raise NotImplementedError("Inference is not supported for YOLO-CROWD models.")
