"""
This module provides a command line interface (CLI) for pulling data using the bank_scrapers API.
"""

# Standard Library Imports
import argparse
import textwrap
import traceback
from typing import Dict, List, Union
import json
import asyncio

# Non-standard Library Imports
import pandas as pd

# Local Imports
from bank_scrapers.common.log import log, logging_levels

# CLI Func Imports
from bank_scrapers import print_version

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

from bank_scrapers.crypto.bitcoin.driver import get_accounts_info as get_bitcoin
from bank_scrapers.crypto.ethereum.driver import get_accounts_info as get_ethereum


def _get_version(args: argparse.Namespace) -> None:
    """
    A wrapper function for printing the library version
    :param args: The argparse namespace containing args required by this function
    """
    print_version()


async def _get_becu(args: argparse.Namespace) -> None:
    """
    A wrapper function for printing the Pandas response from the base function for CLI functionality
    :param args: The argparse namespace containing args required by this function
    """
    tables: List[pd.DataFrame] = await get_becu(
        username=args.username, password=args.password
    )
    for t in tables:
        print(t.to_string(index=False))


async def _get_chase(args: argparse.Namespace) -> None:
    """
    A wrapper function for printing the Pandas response from the base function for CLI functionality
    :param args: The argparse namespace containing args required by this function
    """
    if args.json_file is not None:
        with open(args.json_file[0]) as f:
            mfa_auth: Union[Dict, None] = json.load(f)
    else:
        mfa_auth: Union[Dict, None] = None

    tables: List[pd.DataFrame] = await get_chase(
        username=args.username, password=args.password, mfa_auth=mfa_auth
    )
    for t in tables:
        print(t.to_string(index=False))


async def _get_fidelity_netbenefits(args: argparse.Namespace) -> None:
    """
    A wrapper function for printing the Pandas response from the base function for CLI functionality
    :param args: The argparse namespace containing args required by this function
    """
    if args.json_file is not None:
        with open(args.json_file[0]) as f:
            mfa_auth: Union[Dict, None] = json.load(f)
    else:
        mfa_auth: Union[Dict, None] = None

    tables: List[pd.DataFrame] = await get_fidelity_nb(
        username=args.username, password=args.password, mfa_auth=mfa_auth
    )
    for t in tables:
        print(t.to_string(index=False))


async def _get_roundpoint(args: argparse.Namespace) -> None:
    """
    A wrapper function for printing the Pandas response from the base function for CLI functionality
    :param args: The argparse namespace containing args required by this function
    """
    if args.json_file is not None:
        with open(args.json_file[0]) as f:
            mfa_auth: Union[Dict, None] = json.load(f)
    else:
        mfa_auth: Union[Dict, None] = None

    tables: List[pd.DataFrame] = await get_roundpoint(
        username=args.username, password=args.password, mfa_auth=mfa_auth
    )
    for t in tables:
        print(t.to_string(index=False))


async def _get_smbc_prestia(args: argparse.Namespace) -> None:
    """
    A wrapper function for printing the Pandas response from the base function for CLI functionality
    :param args: The argparse namespace containing args required by this function
    """
    tables: List[pd.DataFrame] = await get_smbc_prestia(
        username=args.username, password=args.password
    )
    for t in tables:
        print(t.to_string(index=False))


async def _get_uhfcu(args: argparse.Namespace) -> None:
    """
    A wrapper function for printing the Pandas response from the base function for CLI functionality
    :param args: The argparse namespace containing args required by this function
    """
    if args.json_file is not None:
        with open(args.json_file[0]) as f:
            mfa_auth: Union[Dict, None] = json.load(f)
    else:
        mfa_auth: Union[Dict, None] = None

    tables: List[pd.DataFrame] = await get_uhfcu(
        username=args.username, password=args.password, mfa_auth=mfa_auth
    )
    for t in tables:
        print(t.to_string(index=False))


async def _get_vanguard(args: argparse.Namespace) -> None:
    """
    A wrapper function for printing the Pandas response from the base function for CLI functionality
    :param args: The argparse namespace containing args required by this function
    """
    if args.json_file is not None:
        with open(args.json_file[0]) as f:
            mfa_auth: Union[Dict, None] = json.load(f)
    else:
        mfa_auth: Union[Dict, None] = None

    tables: List[pd.DataFrame] = await get_vanguard(
        username=args.username, password=args.password, mfa_auth=mfa_auth
    )
    for t in tables:
        print(t.to_string(index=False))


async def _get_zillow(args: argparse.Namespace) -> None:
    """
    A wrapper function for printing the Pandas response from the base function for CLI functionality
    :param args: The argparse namespace containing args required by this function
    """
    tables: List[pd.DataFrame] = await get_zillow(suffix=args.url_suffix[0])
    for t in tables:
        print(t.to_string(index=False))


def _get_kraken(args: argparse.Namespace) -> None:
    """
    A wrapper function for printing the Pandas response from the base function for CLI functionality
    :param args: The argparse namespace containing args required by this function
    """
    tables: List[pd.DataFrame] = get_kraken(
        api_key=args.api_key[0], api_sec=args.secret_key[0]
    )
    for t in tables:
        print(t.to_string(index=False))


async def _get_bitcoin(args: argparse.Namespace) -> None:
    """
    A wrapper function for printing the Pandas response from the base function for CLI functionality
    :param args: The argparse namespace containing args required by this function
    """
    tables: List[pd.DataFrame] = await get_bitcoin(zpub=args.zpub[0])
    for t in tables:
        print(t.to_string(index=False))


def _get_ethereum(args: argparse.Namespace) -> None:
    """
    A wrapper function for printing the Pandas response from the base function for CLI functionality
    :param args: The argparse namespace containing args required by this function
    """
    tables: List[pd.DataFrame] = get_ethereum(address=args.address[0])
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

    # Version
    version_parser = sub_parser.add_parser("version")
    version_parser.set_defaults(func=_get_version)

    # BECU
    becu_parser = sub_parser.add_parser("becu")
    becu_parser.add_argument("username", help="Your username", nargs=1)
    becu_parser.add_argument("password", help="Your password", nargs=1)
    becu_parser.set_defaults(func=_get_becu)

    # Chase
    chase_parser = sub_parser.add_parser(
        "chase",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    chase_parser.add_argument("username", help="Your username", nargs=1)
    chase_parser.add_argument("password", help="Your password", nargs=1)
    chase_parser.add_argument(
        "-j",
        "--json_file",
        metavar="<path_to_json>",
        help=textwrap.dedent(
            """
        A json file containing the MFA authentication options for this driver. 
        This process will wait for a file with the OTP code and the word "Chase" in the directory at `otp_code_location`
        
        Example:
        {
          "otp_contact_option": 1, # Option 1 is SMS, this is recommended
          "otp_contact_option_alternate": 1, # Option 1 is SMS, this is recommended
          "otp_code_location": "/tmp"
        }
        """
        ),
        nargs=1,
    )
    chase_parser.set_defaults(func=_get_chase)

    # Fidelity NetBenefits
    fidelity_nb_parser = sub_parser.add_parser(
        "fidelity-nb",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    fidelity_nb_parser.add_argument("username", help="Your username", nargs=1)
    fidelity_nb_parser.add_argument("password", help="Your password", nargs=1)
    fidelity_nb_parser.add_argument(
        "-j",
        "--json_file",
        metavar="<path_to_json>",
        help=textwrap.dedent(
            """
        A json file containing the MFA authentication options for this driver. 
        This process will wait for a file with the OTP code and the word "NetBenefits" in the dir at `otp_code_location`
        
        Example:
        {
          "otp_code_location": "/tmp"
        }
        """
        ),
        nargs=1,
    )
    fidelity_nb_parser.set_defaults(func=_get_fidelity_netbenefits)

    # RoundPoint
    roundpoint_parser = sub_parser.add_parser(
        "roundpoint",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    roundpoint_parser.add_argument("username", help="Your username", nargs=1)
    roundpoint_parser.add_argument("password", help="Your password", nargs=1)
    roundpoint_parser.add_argument(
        "-j",
        "--json_file",
        metavar="<path_to_json>",
        help=textwrap.dedent(
            """
        A json file containing the MFA authentication options for this driver. 
        This proc waits for a file with the OTP code and the word "Servicing Digital" in the dir at `otp_code_location`
        
        Example:
        {
          "otp_contact_option": 2, # Option 2 is SMS, this is recommended
          "otp_code_location": "/tmp"
        }
        """
        ),
        nargs=1,
    )
    roundpoint_parser.set_defaults(func=_get_roundpoint)

    # SMBC Prestia
    smbc_prestia_parser = sub_parser.add_parser("smbc-prestia")
    smbc_prestia_parser.add_argument("username", help="Your username", nargs=1)
    smbc_prestia_parser.add_argument("password", help="Your password", nargs=1)
    smbc_prestia_parser.set_defaults(func=_get_smbc_prestia)

    # UHFCU
    uhfcu_parser = sub_parser.add_parser(
        "uhfcu",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    uhfcu_parser.add_argument("username", help="Your username", nargs=1)
    uhfcu_parser.add_argument("password", help="Your password", nargs=1)
    uhfcu_parser.add_argument(
        "-j",
        "--json_file",
        metavar="<path_to_json>",
        help=textwrap.dedent(
            """
        A json file containing the MFA authentication options for this driver. 
        Waits for a file with the code and the "University of Hawaii Federal Credit Union" at `otp_code_location`
        
        Example:
        {
          "otp_contact_option": 2, # Option 2 is SMS, this is recommended
          "otp_code_location": "/tmp"
        }
        """
        ),
        nargs=1,
    )
    uhfcu_parser.set_defaults(func=_get_uhfcu)

    # Vanguard
    vanguard_parser = sub_parser.add_parser(
        "vanguard",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    vanguard_parser.add_argument("username", help="Your username", nargs=1)
    vanguard_parser.add_argument("password", help="Your password", nargs=1)
    vanguard_parser.add_argument(
        "-j",
        "--json_file",
        metavar="<path_to_json>",
        help=textwrap.dedent(
            """
        A json file containing the MFA authentication options for this driver. 
        This process will wait for a file with the OTP code and the word "Vanguard" in the dir at `otp_code_location`
        
        Example:
        {
          "otp_contact_option": 2, # Option 2 is SMS, this is recommended
          "otp_code_location": "/tmp"
        }
        """
        ),
        nargs=1,
    )
    vanguard_parser.set_defaults(func=_get_vanguard)

    # Zillow
    zillow_parser = sub_parser.add_parser(
        "zillow",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    zillow_parser.add_argument(
        "url_suffix",
        help=textwrap.dedent(
            """
        The suffix of the Zillow URL (the part after 'homedetails'. 
        Note that you only need to provide the part that ends with "zpid"
        
        For example, this is a valid suffix argument (provided # was replaced by actual digits): ########_zpid
        """
        ),
        nargs=1,
    )
    zillow_parser.set_defaults(func=_get_zillow)

    # Kraken
    kraken_parser = sub_parser.add_parser("kraken")
    kraken_parser.add_argument("api_key", help="Your API Key", nargs=1)
    kraken_parser.add_argument("secret_key", help="Your Secret API Key", nargs=1)
    kraken_parser.set_defaults(func=_get_kraken)

    # Bitcoin
    bitcoin_parser = sub_parser.add_parser("bitcoin")
    bitcoin_parser.add_argument(
        "zpub", help="The zpub key associated with your bitcoin wallet", nargs=1
    )
    bitcoin_parser.set_defaults(func=_get_bitcoin)

    # Ethereum
    ethereum_parser = sub_parser.add_parser("ethereum")
    ethereum_parser.add_argument(
        "address",
        help="The address to associate with the account/wallet. Should be in hex format already",
        nargs=1,
    )
    ethereum_parser.set_defaults(func=_get_ethereum)

    # Parse the args
    args: argparse.Namespace = parser.parse_args()

    # Setup logging
    log_levels: Dict[int, str] = {0: "WARN", 1: "INFO", 2: "DEBUG"}
    user_log_level: str = (
        log_levels[args.verbose] if hasattr(args, "verbose") else log_levels[0]
    )

    log_level: int = logging_levels[user_log_level]
    log.setLevel(log_level)

    log.info("Running with args=%s and log_level=%s", str(args), log_level)

    # Try calling the appropriate handler
    # pylint: disable=W0703
    # noinspection PyBroadException
    try:
        asyncio.run(args.func(args))
    except Exception:
        log.error(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
