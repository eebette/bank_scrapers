"""
Handy functions used across the module
"""

# Standard library imports
from typing import List, Tuple

# Non-Standard Imports
import pandas as pd


def convert_to_prometheus(
    table_list: List[pd.DataFrame],
    institution: str,
    account_column: str,
    symbol: str,
    current_balance_column: str,
) -> List[Tuple[List, float]]:
    """
    Converts standard output of list of pandas table to a Prometheus friendly text exposition
    :param table_list: Standard output of list of pandas table
    :param institution: Text name of the institution to use as Prometheus metric label
    :param account_column: Column name of account identifier
    :param symbol: Asset symbol to use as Prometheus metric label
    :param current_balance_column: Column name of the account balance
    :return: Prometheus friendly metrics for text exposition
    """
    current_balance_metrics: List[Tuple[List, float]] = list()
    for t in table_list:
        for _, row in t.iterrows():
            account: int = int(row[account_column])
            account_type: str = t.name
            current_balance: float = row[current_balance_column]

            current_balance_metrics.append(
                ([institution, account, account_type, symbol], current_balance)
            )

    return current_balance_metrics
