import copy

from Project.DataStream.OBDStreamABC import OBDStreamABC
import threading
import time
import json
import obd

class OBD2Stream(OBDStreamABC):
    _instance = None
    _instance_lock = threading.Lock()  # Lock do obsługi tworzenia instancji

    def __new__(cls, *args, **kwargs):        
        if not cls._instance:
            with cls._instance_lock:
                if not cls._instance:
                    cls._instance = super(OBD2Stream, cls).__new__(cls)
        return cls._instance

    @property
    def CONFIGS_PATH(self):
        return "Project/Configs/Streams/OBD2"
    
    def __init__(self):        
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        super().__init__()
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self._thread = None
        self.current_rpm = 0
        self.current_rpm_timestamp = 0.0
        self.current_speed = 0
        self.current_speed_timestamp = 0.0
        self._initialized = True

    def open(self):
        with self.lock:
            if self.is_opened:
                return
            self.is_opened = True
                
        self.stop_event.clear()
        self._thread = threading.Thread(target=self.initialize_obd, daemon=True)
        self._thread.start()

    def close(self):
        with self.lock:
            if not self.is_opened:
                return                
            self.is_opened = False

        self.stop_event.set()                
        if self.connection:
            self.connection.stop() 

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            self._thread = None
    
    def update_rpm(self, r):
        with self.lock:
            if not r.is_null():
                self.current_rpm = r.value.magnitude
                self.current_rpm_timestamp = time.time()

    def update_speed(self, s):
        with self.lock:
            if not s.is_null():
                self.current_speed = s.value.magnitude
                self.current_speed_timestamp = time.time()

    def initialize_obd(self):        
        self.connection = obd.Async()                 
        timeout = 3
        start_time = time.time()
        
        while self.connection.status() != obd.OBDStatus.CAR_CONNECTED:
            if time.time() - start_time > timeout:
                print("ECU NOT RESPONDING", self.connection.status())
                with self.lock:
                    self.is_opened = False
                return False
            time.sleep(0.1)

        print("ECU Connected: ", self.connection.status())        

        rpm_supported = self.connection.supports(obd.commands.RPM)
        with self.lock:
            self.contract.rpm_supported = rpm_supported
        
        if rpm_supported and self.get_config_value("read_rpm", True):
            self.connection.watch(obd.commands.RPM, callback=self.update_rpm)
        
        speed_supported = self.connection.supports(obd.commands.SPEED)
        with self.lock:
            self.contract.speed_supported = speed_supported
            
        if speed_supported and self.get_config_value("read_speed", True):
            self.connection.watch(obd.commands.SPEED, callback=self.update_speed)
        
        self.connection.start()                        

        while not self.stop_event.is_set():
            time.sleep(0.1)
            with self.lock:
                self.contract.rpm = self.current_rpm
                self.contract.speed = self.current_speed
                self.contract.rpm_timestamp = self.current_rpm_timestamp
                self.contract.speed_timestamp = self.current_speed_timestamp
        return True    
    
    def read(self):
        with self.lock:            
            return copy.deepcopy(self.contract)
        
    def is_open(self):
        with self.lock:
            return self.is_opened