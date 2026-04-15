from Project.DataStream.OBDStreamABC import OBDStreamABC
from Project.obdContract import OBDContract
import threading
import time
import json

class OBDStreamMock(OBDStreamABC):
    @property
    def CONFIGS_PATH(self):
        return "Project/Configs/Streams/Mock"
    
    def __init__(self, contract : OBDContract):
        super().__init__(contract)        

    def open(self):
        pass

    def close(self):
        pass

    def read(self):
        return self.contract