import abc


class ADCReader(abc.ABC):
    @abc.abstractmethod
    def __init__():
        pass

    @abc.abstractmethod
    def setup_adc(self, *args, **kwargs):
        pass

    @abc.abstractmethod
    def read(self):
        pass
