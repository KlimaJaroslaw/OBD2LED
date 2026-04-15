from abc import ABC, abstractmethod
from Project.Configurable.ConfigurableABC import ConfigurableABC
from Project.obdContract import OBDContract

class OBDStreamABC(ConfigurableABC):
    def __init__(self, contract : OBDContract):
        super().__init__()
        self.contract = contract
        self.is_opened = False

    def is_open(self):
        return self.is_opened
    
    @abstractmethod
    def open(self):
        pass                

    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def read(self):
        pass