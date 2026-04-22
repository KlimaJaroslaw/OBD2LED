from abc import ABC, abstractmethod
from Project.Configurable.ConfigurableABC import ConfigurableABC
from Project.DataStream.OBDStreamABC import OBDStreamABC
from Project.obdContract import OBDContract

class LEDControllerABC(ConfigurableABC):

    def __init__(self, stream: OBDStreamABC):
        super().__init__()
        self._stream = stream

        