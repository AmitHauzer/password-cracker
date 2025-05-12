
"""
Israeli phone format
"""

from .base_formats import FormatStrategy


class IsraeliPhoneFormat(FormatStrategy):
    """
    Format an integer in [500_000_000 .. 599_999_999] into "05X-XXXXXXX".
    E.g. 500000000 → "050-0000000", 599999999 → "059-9999999"
    """

    @property
    def min_value(self) -> int:
        """Lowest integer in the domain."""
        return 500_000_000

    @property
    def max_value(self) -> int:
        """Highest integer in the domain."""
        return 599_999_999

    def number_to_string(self, num: int) -> str:
        """Format a single integer into its target string."""
        s = f"{num:09d}"
        return f"05{s[1:2]}-{s[2:]}"
