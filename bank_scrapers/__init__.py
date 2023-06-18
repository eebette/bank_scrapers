"""
Provides library level metadata and constants.
"""

NAME: str = "bank_scrapers"
VERSION: str = "1.0.2"


def version() -> str:
    """Returns the version number of this library."""
    return VERSION


def print_version() -> None:
    """Prints the version number of this library"""
    print(version())


def print_redvox_info() -> None:
    """
    Prints information about this library to standard out.
    """

    print()
    print(f"version: {VERSION}")
    print()
