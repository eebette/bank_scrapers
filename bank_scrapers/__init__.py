"""
Provides library level metadata and constants.
"""

import os

NAME: str = "bank_scrapers"
VERSION: str = "1.3.1"
ROOT_DIR: str = os.path.dirname(os.path.abspath(__file__))


def version() -> str:
    """Returns the version number of this library."""
    return VERSION


def print_version() -> None:
    """Prints the version number of this library"""
    print(version())
