"""
This file provides the get_accounts_info() function for aN Ethereum address

Example Usage:
```
tables = get_accounts_info(address="{address}")
for t in tables:
    print(t.to_string())
```
"""

# Standard Library Imports
from typing import List, Tuple
import pandas as pd

# Non-Standard Imports
from web3 import Web3
from eth_typing.evm import ChecksumAddress, HexAddress, HexStr

# Local Imports
from bank_scrapers.common.functions import convert_to_prometheus

# Institution info
INSTITUTION: str = "ETHEREUM"
SYMBOL: str = "ETH"

# Logon page
HOMEPAGE: str = "https://cloudflare-eth.com/"


def parse_accounts_summary(address: str, balance: float) -> pd.DataFrame:
    """
    Post-processing of the table data
    :param address: The address to associate with the account/wallet
    :param balance: The balance of the account/wallet
    :return: A pandas dataframe of the data
    """
    # Create a simple dataframe from the input amount
    df: pd.DataFrame = pd.DataFrame(
        data={
            "address": [address],
            "balance": [balance],
            "symbol": [SYMBOL],
            "account_type": ["cryptocurrency"],
        }
    )

    # Return the dataframe
    return df


def get_accounts_info(
    address: str, prometheus: bool = False
) -> List[pd.DataFrame] | List[Tuple[List, float]]:
    """
    Gets the accounts info for a given user/pass as a list of pandas dataframes
    :param address: The address to associate with the account/wallet. Should be in hex format already
    :param prometheus: True/False value for exporting as Prometheus-friendly exposition
    :return: A list of pandas dataframes of accounts info tables
    """
    # Fix typing for the hex address
    checksum: ChecksumAddress = ChecksumAddress(HexAddress(HexStr(address)))

    # Connect to the node
    web3: Web3 = Web3(Web3.HTTPProvider(HOMEPAGE))

    # Get and convert the balance from wei to eth
    balance_wei: int = web3.eth.get_balance(checksum)
    balance: float = web3.from_wei(balance_wei, "ether")

    # Get the account balance
    return_tables: List[pd.DataFrame] = [parse_accounts_summary(address, balance)]

    # Convert to Prometheus exposition if flag is set
    if prometheus:
        return_tables: List[Tuple[List, float]] = convert_to_prometheus(
            return_tables,
            INSTITUTION,
            "address",
            "symbol",
            "balance",
            "account_type",
        )

    return return_tables
