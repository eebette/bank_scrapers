"""
This file provides the get_accounts_info() function for a Bitcoin zpub address

Example Usage:
```
tables = get_accounts_info(zpub="{zpub}")
for t in tables:
    print(t.to_string())
```
"""

# Standard Library Imports
from typing import List, Tuple, Union
from datetime import datetime
import pandas as pd

# Non-Standard Imports
from undetected_playwright.async_api import (
    async_playwright,
    Playwright,
    Page,
    Locator,
    expect,
    Browser,
)
from pyvirtualdisplay import Display

# Local Imports
from bank_scrapers import ROOT_DIR
from bank_scrapers.common.log import log
from bank_scrapers.common.types import PrometheusMetric
from bank_scrapers.common.functions import convert_to_prometheus, get_usd_rate_crypto
from bank_scrapers.scrapers.common.functions import screenshot_on_timeout

# Institution info
INSTITUTION: str = "BITCOIN"
SYMBOL: str = "BTC"

# Logon page
HOMEPAGE: str = "https://blockpath.com/search/addr?q="

# Timeout
TIMEOUT: int = 60 * 1000

# Error screenshot config
ERROR_DIR: str = f"{ROOT_DIR}/errors"


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def get_account_balance(page: Page) -> float:
    """
    Gets the account/wallet balance from the webpage
    :param page: The browser application
    :return: A float containing the account/wallet balance
    """
    log.info(f"Getting account balance from page...")

    log.info("Waiting for account balance to be visible...")
    prefix_locator: Locator = page.locator("div[id='addressFinalBalance']")
    await expect(prefix_locator.first).to_be_visible(timeout=TIMEOUT)

    prefixes: List[Locator] = await prefix_locator.all()
    dollars: str = str()
    for prefix in prefixes:
        prefix_text_content: str = await prefix.text_content()
        if len(prefix_text_content) > 0:
            dollars: str = prefix_text_content

    suffix_locator: Locator = page.locator("div[id='addressFinalBalanceDecimal']")
    await expect(suffix_locator.first).to_be_visible(timeout=TIMEOUT)

    suffixes: List[Locator] = await suffix_locator.all()
    cents: str = str()
    for suffix in suffixes:
        suffix_text_content: str = await suffix.text_content()
        if len(suffix_text_content) > 0:
            cents: str = suffix_text_content

    return float(dollars + cents)


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


async def run(
    playwright: Playwright, zpub: str, prometheus: bool = False
) -> Union[List[pd.DataFrame], Tuple[List[PrometheusMetric], List[PrometheusMetric]]]:
    """
    Gets the accounts info for a given user/pass as a list of pandas dataframes
    :param playwright: The playwright object for running this script
    :param zpub: Your wallet's zpub address
    :param prometheus: True/False value for exporting as Prometheus-friendly exposition
    :return: A list of pandas dataframes of accounts info tables
    """
    # Instantiate browser
    browser: Browser = await playwright.chromium.launch(
        channel="chrome",
        headless=False,
        args=["--disable-blink-features=AutomationControlled"],
    )
    page: Page = await browser.new_page()

    # Access the site with the given zpub as a search parameter
    log.info(f"Accessing {HOMEPAGE}{zpub}...")
    await page.goto(f"{HOMEPAGE}{zpub}", timeout=TIMEOUT, wait_until="load")

    # Get the account balance
    account_balance: float = await get_account_balance(page)

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
    # Instantiate the virtual display
    with Display(visible=False, size=(1280, 720)):
        async with async_playwright() as playwright:
            return await run(playwright, zpub, prometheus)
