"""
Custom classes used in the module
"""

from typing import TypedDict, Union


class ChaseMfaAuth(TypedDict):
    otp_contact_option: Union[int, str]
    otp_contact_option_alternate: int
    otp_code_location: str
