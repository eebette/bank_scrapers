"""
Custom classes used in the module
"""

from typing import TypedDict


class MfaAuth(TypedDict):
    otp_contact_option: int
    otp_code_location: str


class ChaseMfaAuth(TypedDict):
    otp_contact_option: int
    otp_contact_option_alternate: int
    otp_code_location: str


class FidelityNetBenefitsMfaAuth(TypedDict):
    otp_code_location: str