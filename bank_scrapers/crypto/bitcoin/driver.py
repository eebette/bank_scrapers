"""
This file provides the get_accounts_info() function for a Bitcoin zpub address

Balances are computed locally by deriving the wallet's BIP-84 addresses from the zpub and summing their UTXO
balances via the mempool.space REST API. No browser or third-party wallet-explorer site is involved.

Example Usage:
```
tables = get_accounts_info(zpub="{zpub}")
for t in tables:
    print(t.to_string())
```
"""

# Standard Library Imports
from time import sleep
from typing import List, Tuple, Union

# Non-Standard Imports
import pandas as pd
import requests
from embit import bip32, script
from embit.bip32 import HDKey
from embit.networks import NETWORKS

# Local Imports
from bank_scrapers.common.log import log
from bank_scrapers.common.types import PrometheusMetric
from bank_scrapers.common.functions import convert_to_prometheus, get_usd_rate_crypto

# Institution info
INSTITUTION: str = "BITCOIN"
SYMBOL: str = "BTC"

# Balance API
API_URL: str = "https://mempool.space/api/address"

# BIP-44 gap limit: stop scanning a chain after this many consecutive unused addresses
GAP_LIMIT: int = 20

# Timeout (seconds, per API request)
TIMEOUT: int = 30


def get_account_balance(zpub: str) -> float:
    """
    Gets the wallet balance by deriving the zpub's BIP-84 receive/change addresses and summing their balances
    :param zpub: The wallet's zpub address
    :return: A float containing the account/wallet balance in BTC
    """
    log.info(f"Deriving addresses and querying balances via {API_URL}...")
    hd: HDKey = bip32.HDKey.from_string(zpub)

    balance_sats: int = 0
    for chain in (0, 1):
        gap: int = 0
        index: int = 0
        while gap < GAP_LIMIT:
            address: str = script.p2wpkh(hd.derive([chain, index])).address(
                NETWORKS["main"]
            )
            response: requests.Response = requests.get(
                f"{API_URL}/{address}", timeout=TIMEOUT
            )
            response.raise_for_status()
            stats: dict = response.json()

            chain_stats: dict = stats["chain_stats"]
            mempool_stats: dict = stats["mempool_stats"]
            balance_sats += (
                chain_stats["funded_txo_sum"] - chain_stats["spent_txo_sum"]
            ) + (mempool_stats["funded_txo_sum"] - mempool_stats["spent_txo_sum"])

            used: bool = chain_stats["tx_count"] + mempool_stats["tx_count"] > 0
            gap = 0 if used else gap + 1
            index += 1
            sleep(0.2)

    balance: float = balance_sats / 1e8
    log.info(f"Wallet balance resolved from {index} derived addresses.")
    return balance


def parse_accounts_summary(zpub: str, balance: float) -> pd.DataFrame:
    """
    Post-processing of the table data
    :param zpub: The zpub to associate with the account/wallet
    :param balance: The balance of the account/wallet
    :return: A pandas dataframe of the data
    """
    # Create a simple dataframe from the input amount
    df: pd.DataFrame = pd.DataFrame(
        data={
            "zpub": [zpub],
            "balance": [balance],
            "symbol": [SYMBOL],
            "account_type": ["cryptocurrency"],
            "usd_value": [get_usd_rate_crypto(SYMBOL)],
        }
    )

    # Return the dataframe
    return df


async def get_accounts_info(
    zpub: str,
    prometheus: bool = False,
) -> Union[List[pd.DataFrame], Tuple[List[PrometheusMetric], List[PrometheusMetric]]]:
    """
    Gets the accounts info for a given user/pass as a list of pandas dataframes
    :param zpub: Your wallet's zpub address
    :param prometheus: True/False value for exporting as Prometheus-friendly exposition
    :return: A list of pandas dataframes of accounts info tables
    """
    # Get the account balance
    account_balance: float = get_account_balance(zpub)

    return_tables: List[pd.DataFrame] = [parse_accounts_summary(zpub, account_balance)]

    # Convert to Prometheus exposition if flag is set
    if prometheus:
        balances: List[PrometheusMetric] = convert_to_prometheus(
            return_tables,
            INSTITUTION,
            "zpub",
            "symbol",
            "balance",
            "account_type",
        )

        asset_values: List[PrometheusMetric] = convert_to_prometheus(
            return_tables,
            INSTITUTION,
            "zpub",
            "symbol",
            "usd_value",
            "account_type",
        )

        return_tables: Tuple[List[PrometheusMetric], List[PrometheusMetric]] = (
            balances,
            asset_values,
        )

    return return_tables
