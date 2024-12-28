"""
Handy functions used across the module
"""

# Standard library imports
from typing import List
import os
from time import sleep
from datetime import date, timedelta
import re

# Non-Standard Imports
import pandas as pd
from currency_converter import CurrencyConverter
import yfinance as yf

# Local Imports
from bank_scrapers.common.log import log
from bank_scrapers.common.types import PrometheusMetric


def get_usd_rate(symbol: str) -> float:
    """
    Get the USD conversion rate of a given forex symbol
    :param symbol: The 3 letter forex symbol to convert to USD
    :return: A float of the USD value of 1 unit of the given forex symbol
    """
    log.info(f"Getting conversion rate of {symbol.upper()} to USD...")
    return CurrencyConverter().convert(1, symbol.upper(), "USD")


def get_usd_rate_crypto(symbol: str) -> float:
    """
    Get the USD conversion rate of a given cryptocurrency symbol
    :param symbol: The 3 letter cryptocurrency symbol to convert to USD
    :return: A float of the USD value of 1 unit of the given cryptocurrency symbol
    """
    try:
        log.info(f"Getting value of {symbol.upper()}-USD from YFinance...")
        return yf.download(
            f"{symbol.upper()}-USD",
            date.today() - timedelta(days=2),
            date.today() - timedelta(),
            progress=False,
        )["Close"].values[0]
    except IndexError:
        log.warning(
            f"Couldn't find value of {symbol.upper()}-USD from YFinance! Filling with 0.0 instead."
        )
        return 0.0


def convert_to_prometheus(
    table_list: List[pd.DataFrame],
    institution: str,
    account_column: str,
    symbol_column: str,
    current_balance_column: str,
    account_type_column: str,
) -> List[PrometheusMetric]:
    """
    Converts standard output of list of pandas table to a Prometheus friendly text exposition
    :param table_list: Standard output of list of pandas table
    :param institution: Text name of the institution to use as Prometheus metric label
    :param account_column: Column name of account identifier
    :param symbol_column: Column name of the asset symbol to use as Prometheus metric label
    :param current_balance_column: Column name of the account balance
    :param account_type_column: Column name of the account type (credit, deposit, etc.)
    :return: Prometheus friendly metrics for text exposition
    """
    log.info(
        f"Creating Prometheus metric from columns {account_column}, {current_balance_column}, {account_type_column}, "
        f"and {symbol_column}..."
    )
    current_balance_metrics: List[PrometheusMetric] = list()
    for t in table_list:
        if all(
            [
                account_column in t.columns,
                current_balance_column in t.columns,
                account_type_column in t.columns,
                symbol_column in t.columns,
            ]
        ):
            for _, row in t.iterrows():
                account: str = row[account_column]
                account_type: str = row[account_type_column]
                current_balance: float = row[current_balance_column]
                symbol: str = row[symbol_column]

                current_balance_metric: PrometheusMetric = (
                    [institution, account, account_type, symbol],
                    current_balance,
                )
                current_balance_metrics.append(current_balance_metric)

    try:
        assert current_balance_metrics
        log.info(f"Prometheus metrics created.")
    except AssertionError:
        log.error(
            f"No tables in output list. Make sure at least one table in the output contains columns {account_column}, "
            f"{current_balance_column}, {account_type_column}, and {symbol_column}."
        )
        raise

    return current_balance_metrics


def wait_for_path_to_exist(filepath: str, timeout: int) -> None:
    """
    Waits for a file path to exist before passing
    :param filepath: The path to the directory for which to wait
    :param timeout: Timeout parameter that will throw a TimeoutError if path doesn't exist
    """
    log.info(f"Waiting for path at {filepath}")
    i = 0
    while not os.path.exists(filepath):
        sleep(1)
        i += 1
        if i >= (timeout / 1000):
            raise TimeoutError("File path doesn't exist!")

    log.info(f"Found {filepath}")
    pass


def wait_for_files_in_dir(filepath: str, timeout: int) -> None:
    """
    Waits for a file to exist in a directory before passing
    :param filepath: The path to the directory for which to wait
    :param timeout: Timeout parameter that will throw a TimeoutError if path doesn't exist
    """
    log.info(f"Waiting for files in {filepath}")
    i = 0
    while not os.listdir(filepath):
        sleep(1)
        i += 1
        if i >= (timeout / 1000):
            raise TimeoutError("No files in file path!")

    log.info(f"Found files in {filepath}")
    pass


def search_files_for_int(
    filepath: str,
    match_string: str,
    min_length: int,
    max_length: int,
    timeout: int,
    file_ext: str = ".txt",
    reverse: bool = False,
    delay: int = 30,
) -> str:
    """
    Searches files in a directory for an integer of specific length, and returns the integer
    :param filepath: The file path at which a file containing the string (for which to search) will exist
    :param match_string: A substring to match in the file before searching the file for the int
    :param min_length: Minimum length of the returned integer
    :param max_length: Maximum length of the returned integer
    :param timeout: Timeout in ms parameter that will throw a TimeoutError if path doesn't exist
    :param file_ext: Extension of files to search in the target directory
    :param reverse: Set to True to search the files in reverse-alphabetical order
    :param delay: Optional delay parameter to use before starting to recurse the files in the file path
    """
    wait_for_path_to_exist(filepath, timeout)
    wait_for_files_in_dir(filepath, timeout)

    total_delay: int = 0
    while True:
        if total_delay >= (timeout / 1000):
            raise TimeoutError(f"OTP code not found after {timeout} seconds")

        sleep(delay)
        total_delay += delay
        for file in sorted(os.listdir(filepath), reverse=reverse)[:2]:
            filename: str = os.fsdecode(file)
            if filename.endswith(file_ext):
                full_filepath: str = os.path.join(filepath, filename)
                log.info(f"Checking {full_filepath} for OTP...")
                with open(full_filepath, "r") as text:
                    text_content: str = text.read().replace("\n", "")

                if re.compile(r"^.*{}(\s+|:\s).*".format(match_string)).match(
                    text_content
                ):
                    code: str = re.findall(
                        rf"\d{{{min_length},{max_length}}}", text_content
                    )[0]

                    log.info(f"OTP found.")
                    log.debug(f"OTP: {code}")
                    return code
