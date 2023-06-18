"""
This module provides a command line interface (CLI) for pulling data using the bank_scrapers API.
"""
# Standard Library Imports
import argparse
import sys
import tempfile
from pathlib import Path
from typing import Dict, List

# Non-standard Library Imports
import pandas as pd

# Local Imports
from bank_scrapers.common.log import log, logging_levels

# CLI Func Imports
from bank_scrapers.scrapers.becu.driver import get_accounts_info as get_becu
from bank_scrapers.scrapers.chase.driver import get_accounts_info as get_chase
from bank_scrapers.scrapers.fidelity_netbenefits.driver import (
    get_accounts_info as get_fidelity_nb,
)
from bank_scrapers.scrapers.roundpoint.driver import get_accounts_info as get_roundpoint
from bank_scrapers.scrapers.smbc_prestia.driver import (
    get_accounts_info as get_smbc_prestia,
)
from bank_scrapers.scrapers.uhfcu.driver import get_accounts_info as get_uhfcu
from bank_scrapers.scrapers.vanguard.driver import get_accounts_info as get_vanguard
from bank_scrapers.scrapers.zillow.driver import get_accounts_info as get_zillow
from bank_scrapers.api_wrappers.kraken.driver import get_accounts_info as get_kraken


def _get_becu(args: argparse.Namespace) -> None:
    """
    A wrapper function for printing the Pandas response from the base function for CLI functionality
    :param args: The argparse namespace containing args required by this function
    """
    tables: List[pd.DataFrame] = get_becu(
        username=args.username, password=args.password
    )
    for t in tables:
        print(t.to_string(index=False))


def _get_chase(args: argparse.Namespace) -> None:
    """
    A wrapper function for printing the Pandas response from the base function for CLI functionality
    :param args: The argparse namespace containing args required by this function
    """
    tables: List[pd.DataFrame] = get_chase(
        username=args.username, password=args.password
    )
    for t in tables:
        print(t.to_string(index=False))


def _get_fidelity_netbenefits(args: argparse.Namespace) -> None:
    """
    A wrapper function for printing the Pandas response from the base function for CLI functionality
    :param args: The argparse namespace containing args required by this function
    """
    tempfile.tempdir = f"{Path.home()}"
    with tempfile.TemporaryDirectory() as tmp_dir:
        tables: List[pd.DataFrame] = get_fidelity_nb(
            username=args.username, password=args.password, tmp_dir=tmp_dir
        )
        for t in tables:
            print(t.to_string(index=False))


def _get_roundpoint(args: argparse.Namespace) -> None:
    """
    A wrapper function for printing the Pandas response from the base function for CLI functionality
    :param args: The argparse namespace containing args required by this function
    """
    tables: List[pd.DataFrame] = get_roundpoint(
        username=args.username, password=args.password
    )
    for t in tables:
        print(t.to_string(index=False))


def _get_smbc_prestia(args: argparse.Namespace) -> None:
    """
    A wrapper function for printing the Pandas response from the base function for CLI functionality
    :param args: The argparse namespace containing args required by this function
    """
    tables: List[pd.DataFrame] = get_smbc_prestia(
        username=args.username, password=args.password
    )
    for t in tables:
        print(t.to_string(index=False))


def _get_uhfcu(args: argparse.Namespace) -> None:
    """
    A wrapper function for printing the Pandas response from the base function for CLI functionality
    :param args: The argparse namespace containing args required by this function
    """
    tables: List[pd.DataFrame] = get_uhfcu(
        username=args.username, password=args.password
    )
    for t in tables:
        print(t.to_string(index=False))


def _get_vanguard(args: argparse.Namespace) -> None:
    """
    A wrapper function for printing the Pandas response from the base function for CLI functionality
    :param args: The argparse namespace containing args required by this function
    """
    tempfile.tempdir = f"{Path.home()}"
    with tempfile.TemporaryDirectory() as tmp_dir:
        tables: List[pd.DataFrame] = get_vanguard(
            username=args.username, password=args.password, tmp_dir=tmp_dir
        )
        for t in tables:
            print(t.to_string(index=False))


def _get_zillow(args: argparse.Namespace) -> None:
    """
    A wrapper function for printing the Pandas response from the base function for CLI functionality
    :param args: The argparse namespace containing args required by this function
    """
    tables: List[pd.DataFrame] = get_zillow(suffix=args.url_suffix[0])
    for t in tables:
        print(t.to_string(index=False))


def _get_kraken(args: argparse.Namespace) -> None:
    """
    A wrapper function for printing the Pandas response from the base function for CLI functionality
    :param args: The argparse namespace containing args required by this function
    """
    tables: List[pd.DataFrame] = get_kraken(api_key=args.api_key, api_sec=args.api_sec)
    for t in tables:
        print(t.to_string(index=False))


def main() -> None:
    """
    Entry point into the CLI.
    """

    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        "bank-scrape",
        description="Command line interface for pulling accounts info using the bank_scrapers library",
    )

    parser.add_argument(
        "--verbose", "-v", help="Enable verbose logging", action="count", default=0
    )

    sub_parser = parser.add_subparsers()
    sub_parser.required = True
    sub_parser.dest = "command"

    # BECU
    becu_parser = sub_parser.add_parser("becu")
    becu_parser.add_argument("username", help="Your username", nargs=1)
    becu_parser.add_argument("password", help="Your password", nargs=1)
    becu_parser.set_defaults(func=_get_becu)

    # Chase
    chase_parser = sub_parser.add_parser("chase")
    chase_parser.add_argument("username", help="Your username", nargs=1)
    chase_parser.add_argument("password", help="Your password", nargs=1)
    chase_parser.set_defaults(func=_get_chase)

    # Fidelity NetBenefits
    fidelity_nb_parser = sub_parser.add_parser("fidelity-nb")
    fidelity_nb_parser.add_argument("username", help="Your username", nargs=1)
    fidelity_nb_parser.add_argument("password", help="Your password", nargs=1)
    fidelity_nb_parser.set_defaults(func=_get_fidelity_netbenefits)

    # RoundPoint
    roundpoint_parser = sub_parser.add_parser("roundpoint")
    roundpoint_parser.add_argument("username", help="Your username", nargs=1)
    roundpoint_parser.add_argument("password", help="Your password", nargs=1)
    roundpoint_parser.set_defaults(func=_get_roundpoint)

    # SMBC Prestia
    smbc_prestia_parser = sub_parser.add_parser("smbc-prestia")
    smbc_prestia_parser.add_argument("username", help="Your username", nargs=1)
    smbc_prestia_parser.add_argument("password", help="Your password", nargs=1)
    smbc_prestia_parser.set_defaults(func=_get_smbc_prestia)

    # UHFCU
    uhfcu_parser = sub_parser.add_parser("uhfcu")
    uhfcu_parser.add_argument("username", help="Your username", nargs=1)
    uhfcu_parser.add_argument("password", help="Your password", nargs=1)
    uhfcu_parser.set_defaults(func=_get_uhfcu)

    # Vanguard
    vanguard_parser = sub_parser.add_parser("vanguard")
    vanguard_parser.add_argument("username", help="Your username", nargs=1)
    vanguard_parser.add_argument("password", help="Your password", nargs=1)
    vanguard_parser.set_defaults(func=_get_vanguard)

    # Zillow
    zillow_parser = sub_parser.add_parser("zillow")
    zillow_parser.add_argument(
        "url_suffix",
        help="""
            The suffix of the Zillow URL (the part after 'homedetails'. Note that you only need to provide the part that
             ends with "zpid"\n
            For example, this is a valid suffix argument (provided # was replaced by actual digits): ########_zpid
            """,
        nargs=1,
    )
    zillow_parser.set_defaults(func=_get_zillow)

    # Kraken
    kraken_parser = sub_parser.add_parser("kraken")
    kraken_parser.add_argument("api key", help="Your API Key", nargs=1)
    kraken_parser.add_argument("secret key", help="Your Secret API Key", nargs=1)
    kraken_parser.set_defaults(func=_get_kraken)

    # Parse the args
    args = parser.parse_args()

    # Setup logging
    log_levels: Dict[int, str] = {0: "WARN", 1: "INFO", 2: "DEBUG"}
    user_log_level = (
        log_levels[args.verbose] if hasattr(args, "verbose") else log_levels[0]
    )

    log_level: str = (logging_levels[user_log_level])
    log.setLevel(log_level)

    log.info("Running with args=%s and log_level=%s", str(args), log_level)

    # Try calling the appropriate handler
    # pylint: disable=W0703
    try:
        args.func(args)
    except Exception as e:
        log.error("Encountered an error: %s", str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
