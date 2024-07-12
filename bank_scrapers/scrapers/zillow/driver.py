"""
This file provides the get_accounts_info() function for Zillow (https://www.zillow.com)

Example Usage:
```
tables = get_accounts_info(suffix="{url_suffix_for_property}")
for t in tables:
    print(t.to_string())
```
"""

# Standard Library Imports
from typing import List, Tuple, Union
from datetime import datetime

# Non-Standard Imports
import pandas as pd
from undetected_playwright.async_api import (
    async_playwright,
    Playwright,
    Page,
    Locator,
    Browser,
)
from pyvirtualdisplay import Display

# Local Imports
from bank_scrapers import ROOT_DIR
from bank_scrapers.scrapers.common.functions import screenshot_on_timeout
from bank_scrapers.common.functions import convert_to_prometheus
from bank_scrapers.common.log import log
from bank_scrapers.common.types import PrometheusMetric

# Institution info
INSTITUTION: str = "Zillow"
SYMBOL: str = "USD"

# Logon page
HOMEPAGE = "https://www.zillow.com/homedetails/"

# Timeout
TIMEOUT: int = 60 * 1000

# Error screenshot config
ERROR_DIR: str = f"{ROOT_DIR}/errors"


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def logon(page: Page, homepage: str, suffix: str) -> None:
    """
    Opens and signs on to an account
    :param page: The browser application
    :param homepage: The logon url to initially navigate
    :param suffix: The URL suffix after 'https://www.zillow.com/homedetails/' to use to identify the property
    """
    # Property Page
    log.info(f"Accessing: {homepage + suffix}")
    await page.goto(homepage + suffix, timeout=TIMEOUT, wait_until="load")


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def seek_accounts_data(page: Page) -> Tuple[str, str]:
    """
    Navigate the website and find the accounts data for the user
    :param page: The Chrome browser application
    :return: The web element of the accounts data
    """
    log.info(f"Finding zestimate element...")
    zestimate_element: Locator = (
        page.locator("span[data-testid='zestimate-text']").get_by_text("$").first
    )
    zestimate: str = await zestimate_element.text_content()

    log.info(f"Finding address element...")
    address_element: Locator = page.locator("div[class='summary-container'] h1")
    address: str = await address_element.text_content()

    return address, zestimate


def parse_accounts_summary(address: str, zestimate: str) -> pd.DataFrame:
    """
    Post-processing of the table data
    :param address: The web element containing the address for this property
    :param zestimate: The web element containing the zestimate for this property
    :return: A pandas dataframe of the data
    """
    # Create a simple dataframe from the input amount
    df: pd.DataFrame = pd.DataFrame(
        data={
            "address": [address],
            "zestimate": [zestimate],
            "symbol": [SYMBOL],
            "account_type": ["real_estate"],
            "usd_value": [1.0],
        }
    )

    # Remove non-digits from the value
    df["zestimate"]: pd.DataFrame = df["zestimate"].replace(
        to_replace=r"[^0-9]+", value="", regex=True
    )
    df["zestimate"]: pd.DataFrame = pd.to_numeric(df["zestimate"])

    # Return the dataframe
    return df


async def run(
    playwright: Playwright, suffix: str, prometheus: bool = False
) -> Union[List[pd.DataFrame], Tuple[List[PrometheusMetric], List[PrometheusMetric]]]:
    """
    Gets the accounts info for a given user/pass as a list of pandas dataframes
    :param playwright: The playwright object for running this script
    :param suffix: The URL suffix after 'https://www.zillow.com/homedetails/' to use to identify the property
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

    # Navigate to the logon page and submit credentials
    await logon(page, HOMEPAGE, suffix)

    # Navigate the site and download the accounts data
    address: str
    zestimate: str
    address, zestimate = await seek_accounts_data(page)
    accounts_data_df: pd.DataFrame = parse_accounts_summary(address, zestimate)

    # Process tables
    return_tables: List[pd.DataFrame] = [accounts_data_df]

    # Convert to Prometheus exposition if flag is set
    if prometheus:
        balances: List[PrometheusMetric] = convert_to_prometheus(
            return_tables,
            INSTITUTION,
            "address",
            "symbol",
            "zestimate",
            "account_type",
        )

        asset_values: List[PrometheusMetric] = convert_to_prometheus(
            return_tables,
            INSTITUTION,
            "address",
            "symbol",
            "usd_value",
            "account_type",
        )

        return_tables: Tuple[List[PrometheusMetric], List[PrometheusMetric]] = (
            balances,
            asset_values,
        )

    # Return list of pandas df
    return return_tables


async def get_accounts_info(
    suffix: str, prometheus: bool = False
) -> Union[List[pd.DataFrame], Tuple[List[PrometheusMetric], List[PrometheusMetric]]]:
    """
    Gets the accounts info for a given user/pass as a list of pandas dataframes
    :param suffix: The URL suffix after 'https://www.zillow.com/homedetails/' to use to identify the property
    :param prometheus: True/False value for exporting as Prometheus-friendly exposition
    :return: A list of pandas dataframes of accounts info tables
    """
    # Instantiate the virtual display
    with Display(visible=False, size=(1280, 720)):
        async with async_playwright() as playwright:
            return await run(playwright, suffix, prometheus)
