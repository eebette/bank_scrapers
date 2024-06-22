"""
Custom classes used in the module
"""

from typing import TypedDict


class ChaseMfaAuth(TypedDict):
    otp_contact_option: int
    otp_contact_option_alternate: int
    otp_code_location: str
