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
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from undetected_chromedriver import Chrome, ChromeOptions

# Local Imports
from bank_scrapers import ROOT_DIR
from bank_scrapers.scrapers.common.functions import (
    start_chromedriver,
    get_chrome_options,
    wait_and_find_element,
    screenshot_on_timeout,
)
from bank_scrapers.common.log import log
from bank_scrapers.common.functions import convert_to_prometheus, get_usd_rate_crypto
from bank_scrapers.common.types import PrometheusMetric

# Institution info
INSTITUTION: str = "BITCOIN"
SYMBOL: str = "BTC"

# Logon page
HOMEPAGE: str = "https://blockpath.com/search/addr?q="

# Timeout
TIMEOUT: int = 60

# Chrome config
USER_AGENT: str = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.50 Safari/537.36"
)
CHROME_OPTIONS: List[str] = [
    f"user-agent={USER_AGENT}",
    "--no-sandbox",
    "--window-size=1920,1080",
    "--disable-gpu",
    "--headless",
    "--allow-running-insecure-content",
]

# Error screenshot config
ERROR_DIR: str = f"{ROOT_DIR}/errors"


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
def get_account_balance(driver: Chrome, wait: WebDriverWait) -> float:
    """
    Gets the account/wallet balance from the webpage
    :param driver: The browser application
    :param wait: WebDriverWait object for the driver
    :return: A float containing the account/wallet balance
    """
    log.info(f"Getting account balance from page...")
    prefix: WebElement = wait_and_find_element(
        driver,
        wait,
        (By.XPATH, "//div[@id='addressFinalBalance' and string-length(text()) > 0]"),
    )
    suffix: WebElement = wait_and_find_element(
        driver,
        wait,
        (
            By.XPATH,
            "//div[@id='addressFinalBalanceDecimal' and string-length(text()) > 0]",
        ),
    )
    log.info(f"Got account balance from page!")
    return float(prefix.text + suffix.text)


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


def get_accounts_info(
    zpub: str, prometheus: bool = False
) -> Union[List[pd.DataFrame], Tuple[List[PrometheusMetric], List[PrometheusMetric]]]:
    """
    Gets the accounts info for a given user/pass as a list of pandas dataframes
    :param zpub: Your wallet's zpub address
    :param prometheus: True/False value for exporting as Prometheus-friendly exposition
    :return: A list of pandas dataframes of accounts info tables
    """
    # Get Driver config
    chrome_options: ChromeOptions = get_chrome_options(CHROME_OPTIONS)
    driver: Chrome = start_chromedriver(chrome_options)
    wait: WebDriverWait = WebDriverWait(driver, TIMEOUT)

    # Access the site with the given zpub as a search parameter
    log.info(f"Accessing {HOMEPAGE}{zpub}...")
    driver.get(f"{HOMEPAGE}{zpub}")

    # Get the account balance
    account_balance: float = get_account_balance(driver, wait)

    # Clean up
    driver.quit()

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
