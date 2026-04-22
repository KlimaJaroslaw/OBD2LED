
from abc import ABC, abstractmethod

import json
import os


class ConfigurableABC(ABC):
    @property
    @abstractmethod
    def CONFIGS_PATH(self):        
        pass

    def __init__(self):        
        #self.all_configs = self.get_configs()
        self.all_configs = self.load_configs(self.CONFIGS_PATH)
        self.static_configs = self.load_configs("Project/Configs/Static")
        self.config = self.all_configs.get("default", {})

    # def get_configs(self):
    #     configs = {}
    #     for filename in os.listdir(self.CONFIGS_PATH):
    #         if filename.endswith('.cfg'):
    #             config_name = filename.replace('.cfg', '')
    #             with open(os.path.join(self.CONFIGS_PATH, filename), 'r') as f:
    #                 configs[config_name] = json.load(f)
    #     return configs

    def set_config(self, config_name):
        self.config = self.all_configs.get(config_name, {})

    def cycle_config(self):
        config_names = list(self.all_configs.keys())
        current_index = config_names.index(self.config.get("name", "default"))
        next_index = (current_index + 1) % len(config_names)
        self.set_config(config_names[next_index])

    def get_config(self):
        return self.config
    
    def get_config_value(self, key, default=None):
        return self.config.get(key, default)
    
    # def load_static_config(self):
    #     configs = {}
    #     for filename in os.listdir(self.CONFIGS_PATH):
    #         if filename.endswith('.cfg'):
    #             config_name = filename.replace('.cfg', '')
    #             with open(os.path.join(self.CONFIGS_PATH, filename), 'r') as f:
    #                 configs[config_name] = json.load(f)
    #     return configs
    
    def load_configs(self, path):
        configs = {}
        for filename in os.listdir(path):
            if filename.endswith('.cfg'):
                config_name = filename.replace('.cfg', '')
                with open(os.path.join(path, filename), 'r') as f:
                    configs[config_name] = json.load(f)
        return configs