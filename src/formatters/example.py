"""
Example stub for future formats
"""

from .base_formats import FormatStrategy


class ExampleFormat(FormatStrategy):
    """
    Example format
    """

    @property
    def min_value(self) -> int:
        return 0

    @property
    def max_value(self) -> int:
        return 9

    def number_to_string(self, num: int) -> str:
        return f"EX-{num}"


if __name__ == "__main__":
    ex = ExampleFormat()
    print(ex.min_value)
    print(ex.number_to_string(4))
    print(ex.max_value)
