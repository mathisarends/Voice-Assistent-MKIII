from abc import ABC, abstractmethod

class SpotifyCommand(ABC):
    @abstractmethod
    def execute(self):
        pass