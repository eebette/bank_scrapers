"""
Provides library level metadata and constants.
"""
from .scrapers import *

NAME: str = "bank_scrapers"
VERSION: str = "1.0.13"


def version() -> str:
    """Returns the version number of this library."""
    return VERSION


def print_version() -> None:
    """Prints the version number of this library"""
    print(version())
