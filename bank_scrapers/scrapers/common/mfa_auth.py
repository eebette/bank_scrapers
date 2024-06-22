"""
Custom classes used in the module
"""

from typing import TypedDict


class MfaAuth(TypedDict):
    otp_contact_option: int
    otp_code_location: str
