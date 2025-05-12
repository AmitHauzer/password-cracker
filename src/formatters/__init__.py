
"""
Formatters for the password cracker.
"""

from formatters.base_formats import FormatStrategy
from formatters.israeli_phone_format import IsraeliPhoneFormat


FORMATTERS: dict[str, FormatStrategy] = {
    "israel_phone": IsraeliPhoneFormat(),
}
