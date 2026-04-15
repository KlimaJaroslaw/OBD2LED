from Project.DataStream.OBDStreamABC import OBDStreamABC
from Project.obdContract import OBDContract
import pandas as pd
import pickle
import threading
import time
import json

class OBDStreamMock(OBDStreamABC):
    @property
    def CONFIGS_PATH(self):
        return "Project/Configs/Streams/Mock"
    
    def __init__(self, contract: OBDContract):
        super().__init__(contract)
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = None
        self._data_index = 0
        self.virtual_time = 0
        self._last_wall_time = None    

    def open(self):
        if self._thread and self._thread.is_alive():
            return

        self.stream_data = self.get_data()
        self.virtual_time = self.stream_data.iloc[0]['timestamp']                
        self._last_wall_time = time.perf_counter()

        self.is_opened = True
        self._stop_event.clear()
        
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self):
        while not self._stop_event.is_set():
            self.stream_action()
            time.sleep(0.1)

    def stream_action(self):
        now = time.perf_counter()
        delta_time = now - self._last_wall_time
        self._last_wall_time = now

        with self._lock:            
            self.virtual_time += delta_time                        
                        
            if self._data_index >= len(self.stream_data) - 1:                
                self._data_index = 0                
                self.virtual_time = self.stream_data.iloc[0]['timestamp']                
                return
                        
            data_changed = False
            while (self._data_index < len(self.stream_data) - 1 and 
                   self.virtual_time >= self.stream_data.iloc[self._data_index + 1]['timestamp']):                
                self._data_index += 1
                data_changed = True
            
            if data_changed:
                current_row = self.stream_data.iloc[self._data_index]
                self.contract.rpm = current_row['rpm']
                self.contract.rpm_timestamp = current_row['timestamp']
                self.contract.speed = current_row['speed']
                self.contract.speed_timestamp = current_row['timestamp']

    def close(self):
        self.is_opened = False
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join()
            self._thread = None

    def read(self):
        with self._lock:
            return self.contract
    
    def get_data(self):
        pickle_path = self.get_config_value("pickle_path")
        with open(pickle_path, 'rb') as f:
            data = pickle.load(f)
        return pd.DataFrame(data)

# class OBDStreamMock(OBDStreamABC):
#     @property
#     def CONFIGS_PATH(self):
#         return "Project/Configs/Streams/Mock"
    
#     def __init__(self, contract: OBDContract):
#         super().__init__(contract)
#         self._lock = threading.Lock()
#         self._stop_event = threading.Event()
#         self._thread = None
#         self._data_index = 0  # To track "stream" position
#         self.virtual_time = 0
#         self._last_wall_time = None  # Tracks actual physical time

#     def __enter__(self):
#         self.open()
#         return self

#     def __exit__(self, exc_type, exc_val, exc_tb):
#         self.close()

#     def open(self):
#         if self._thread and self._thread.is_alive():
#             return  # Already running

#         self.stream_data = self.get_data()
        
#         self.virtual_time = self.stream_data.iloc[0]['timestamp']                
#         self._last_wall_time = time.perf_counter()


#         self.is_open = True
#         self._stop_event.clear()
        
#         self._thread = threading.Thread(target=self._run_loop, daemon=True)
#         self._thread.start()

#     def _run_loop(self):
#         """Internal loop logic."""
#         while not self._stop_event.is_set():
#             self.stream_action()
#             time.sleep(0.1) # Control frequency (e.g., 10Hz)

#     def stream_action(self):
#         now = time.perf_counter()
#         delta_time = now - self._last_wall_time
#         self._last_wall_time = now

#         with self._lock:            
#             self.virtual_time += delta_time                        
                        
#             if self._data_index >= len(self.stream_data) - 1:                
#                 self._data_index = 0                
#                 self.virtual_time = self.stream_data.iloc[0]['timestamp']                
#                 return
                        
#             data_changed = False
#             while (self._data_index < len(self.stream_data) - 1 and 
#                    self.virtual_time >= self.stream_data.iloc[self._data_index + 1]['timestamp']):                
#                 self._data_index += 1
#                 data_changed = True
            
#             if data_changed:
#                 current_row = self.stream_data.iloc[self._data_index]
#                 self.contract.rpm = current_row['rpm']
#                 self.contract.speed = current_row['speed']

#     def close(self):
#         self.is_open = False
#         if self._thread:
#             self._stop_event.set()
#             self._thread.join()
#             self._thread = None

#     def read(self):
#         return self.contract
    
#     def get_data(self):
#         pickle_path = self.get_config_value("pickle_path")
#         with open(pickle_path, 'rb') as f:
#             data = pickle.load(f)
#         df = pd.DataFrame(data)
#         return df