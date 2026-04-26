from abc import abstractmethod, ABC

from config.config_loader import ConfigLoader
from project_root import PROJECT_ROOT


class BaseModel(ABC):
    def __init__(self, dataset_path: str):
        self.config_loader = ConfigLoader()
        self.dataset_path = PROJECT_ROOT / dataset_path

    @abstractmethod
    def run_prediction(self, show: bool = None):
        pass
