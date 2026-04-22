from abc import ABC, abstractmethod
from Project.Configurable.ConfigurableABC import ConfigurableABC
from Project.obdContract import OBDContract

class OBDStreamABC(ConfigurableABC):
    def __init__(self):
        super().__init__()
        self.contract = OBDContract()
        self.is_opened = False
    
    @property
    def is_open(self):
        return self.is_opened
    
    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()    

    @abstractmethod
    def open(self):
        """Logic to start the thread/connection"""
        pass                

    @abstractmethod
    def close(self):
        """Logic to stop the thread/connection"""
        pass

    @abstractmethod
    def read(self):
        """Logic to return data"""
        pass