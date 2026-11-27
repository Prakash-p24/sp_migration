from abc import ABC, abstractmethod


class BaseConverter(ABC):
    """Common interface for source-to-target IR converters."""

    @abstractmethod
    def convert(self, node):
        raise NotImplementedError
