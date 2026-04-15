from Project.Configurable.ConfigurableABC import ConfigurableABC


class MockLEDController(ConfigurableABC):
    @property
    def CONFIGS_PATH(self):
        return "Project/Configs/LEDControllers/Mock"
    
    def __init__(self):
        super().__init__()