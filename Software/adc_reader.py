from abc import ABC


class ADCReader(ABC):
    @abstractmethod
    def __init__():
        pass

    @abstractmethod
    def setup_adc(self, *args, **kwargs):
        pass

    @abstractmethod
    def read(self):
        pass
