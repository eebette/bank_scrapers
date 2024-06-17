"""
Provides library level metadata and constants.
"""

NAME: str = "bank_scrapers"
VERSION: str = "1.0.13"


def version() -> str:
    """Returns the version number of this library."""
    return VERSION


def print_version() -> None:
    """Prints the version number of this library"""
    print(version())


# TODO: logging, master get_accounts_info, cli update, readme update
