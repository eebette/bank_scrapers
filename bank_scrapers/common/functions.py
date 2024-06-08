"""
Handy functions used across the module
"""

# Standard library imports
from typing import List, Tuple
import os
from time import sleep
import re

# Non-Standard Imports
import pandas as pd
import requests


def convert_to_prometheus(
    table_list: List[pd.DataFrame],
    institution: str,
    account_column: str,
    symbol_column: str,
    current_balance_column: str,
    account_type_column: str,
) -> List[Tuple[List, float]]:
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
    current_balance_metrics: List[Tuple[List, float]] = list()

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

                current_balance_metrics.append(
                    ([institution, account, account_type, symbol], current_balance)
                )

    try:
        assert table_list
    except AssertionError as e:
        print(e)
        print(
            f"No tables in output list. Make sure at least one table in the output contains columns {account_column}, "
            f"{current_balance_column}, {account_type_column}, and {symbol_column}."
        )
        exit(1)

    return current_balance_metrics


def wait_for_path_to_exist(filepath: str, timeout: int) -> None:
    """
    Waits for a file path to exist before passing
    :param filepath: The path to the directory for which to wait
    :param timeout: Timeout parameter that will throw a TimeoutError if path doesn't exist
    """
    i = 0
    while not os.path.exists(filepath):
        sleep(1)
        i += 1
        if i == timeout:
            raise TimeoutError("File path doesn't exist!")
    pass


def wait_for_files_in_dir(filepath: str, timeout: int) -> None:
    """
    Waits for a file to exist in a directory before passing
    :param filepath: The path to the directory for which to wait
    :param timeout: Timeout parameter that will throw a TimeoutError if path doesn't exist
    """
    i = 0
    while not os.listdir(filepath):
        sleep(1)
        i += 1
        if i == timeout:
            raise TimeoutError("No files in file path!")
    pass


def search_files_for_int(
    filepath: str,
    match_string: str,
    file_ext: str,
    min_length: int,
    max_length: int,
    timeout: int,
    reverse: bool = False,
    delay=10,
) -> int:
    """
    Searches files in a directory for an integer of specific length, and returns the integer
    :param filepath: The file path at which a file containing the string (for which to search) will exist
    :param match_string: A substring to match in the file before searching the file for the int
    :param file_ext: Extension of files to search in the target directory
    :param min_length: Minimum length of the returned integer
    :param max_length: Maximum length of the returned integer
    :param timeout: Timeout parameter that will throw a TimeoutError if path doesn't exist
    :param reverse: Set to True to search the files in reverse-alphabetical order
    :param delay: Optional delay parameter to use before starting to recurse the files in the file path
    """
    sleep(delay)
    wait_for_path_to_exist(filepath, timeout)
    wait_for_files_in_dir(filepath, timeout)

    for file in sorted(os.listdir(filepath), reverse=reverse):
        filename: str = os.fsdecode(file)
        if filename.endswith(file_ext):
            filepath: str = os.path.join(filepath, filename)

            with open(filepath, "r") as text:
                text_content: str = text.read().replace("\n", "")

            if re.compile(r"^.*{}(\s+|:\s).*".format(match_string)).match(text_content):
                return_int: int = re.findall(
                    rf"\d{{{min_length},{max_length}}}", text_content
                )[0]
                return int(return_int)

    raise Exception(
        f"No integers between {min_length} and {max_length} characters found in any files!"
    )


def get_ticker(company_name):
    """

    :param company_name:
    :return:
    """
    yfinance = "https://query2.finance.yahoo.com/v1/finance/search"
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
    params = {"q": company_name, "quotes_count": 1, "country": "United States"}

    res = requests.get(url=yfinance, params=params, headers={"User-Agent": user_agent})
    data = res.json()

    company_code = data["quotes"][0]["symbol"]
    return company_code


def search_for_dir(cwd: str, target: str) -> str:
    """

    :param cwd:
    :param target:
    :return:
    """
    directory: str = os.path.dirname(os.path.abspath(cwd))

    # Navigate up the directory tree until you reach the target
    while not os.path.exists(os.path.join(directory, target)):
        directory: str = os.path.dirname(directory)

    return directory
