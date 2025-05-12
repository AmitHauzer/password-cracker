from abc import ABC, abstractmethod


class FormatStrategy(ABC):
    @property
    @abstractmethod
    def min_value(self) -> int:
        """Lowest integer in the domain."""
    @property
    @abstractmethod
    def max_value(self) -> int:
        """Highest integer in the domain."""
    @abstractmethod
    def number_to_string(self, num: int) -> str:
        """Format a single integer into its target string."""
