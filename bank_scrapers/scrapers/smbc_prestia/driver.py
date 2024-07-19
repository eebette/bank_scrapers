"""
This file provides the get_accounts_info() function for SMBC Prestia (https://login.smbctb.co.jp)

Example Usage:
```
tables = get_accounts_info(username="{username}", password="{password}")
for t in tables:
    print(t.to_string())
```
"""

# Standard Library Imports
from typing import List, Tuple, Union
from datetime import datetime
import re
from io import StringIO

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
from bank_scrapers.common.functions import convert_to_prometheus, get_usd_rate
from bank_scrapers.common.log import log
from bank_scrapers.common.types import PrometheusMetric
from bank_scrapers.scrapers.common.functions import screenshot_on_timeout

# Institution info
INSTITUTION: str = "SMBC Prestia"

# Logon page
HOMEPAGE: str = (
    "https://login.smbctb.co.jp/ib/portal/POSNIN1prestiatop.prst?LOCALE=en_JP"
)

# Timeout
TIMEOUT: int = 60 * 1000

# Error screenshot config
ERROR_DIR: str = f"{ROOT_DIR}/errors"


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def logon(
    page: Page, username: str, password: str, homepage: str = HOMEPAGE
) -> None:
    """
    Opens and signs on to an account
    :param page: The browser application
    :param username: Your username for logging in
    :param password: Your password for logging in
    :param homepage: The logon url to initially navigate
    """
    # Logon Page
    log.info(f"Accessing: {homepage}")
    await page.goto(homepage, timeout=TIMEOUT, wait_until="load")

    # Enter User
    log.info(f"Finding username element...")
    username_input: Locator = page.locator("input[id='dispuserId']")

    log.info(f"Sending info to username element...")
    log.debug(f"Username: {username}")
    await username_input.press_sequentially(username, delay=100)

    # Enter Password
    log.info(f"Finding password element...")
    password_input: Locator = page.locator("input[id='disppassword']")

    log.info(f"Sending info to password element...")
    await password_input.press_sequentially(password, delay=100)

    # Submit credentials
    log.info(f"Finding submit button element...")
    submit_button: Locator = page.get_by_role("link", name="Sign On")

    log.info(f"Clicking submit button element...")
    async with page.expect_navigation(
        url=re.compile(r"online."), wait_until="load", timeout=TIMEOUT
    ):
        await submit_button.click()


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def seek_accounts_data(page: Page) -> List[Locator]:
    """
    Navigate the website and find the accounts data for the user
    :param page: The Chrome browser application
    :return: The list of web elements of the accounts data
    """
    log.info(f"Finding accounts button element...")
    accounts_button: Locator = page.get_by_role("link", name="Accounts", exact=True)

    log.info(f"Clicking accounts button element...")
    await accounts_button.click()

    log.info(f"Finding balance button element...")
    balance_button: Locator = page.get_by_label("Accounts").get_by_role(
        "link", name="Balance Summary", exact=True
    )

    log.info(f"Clicking balance button element...")
    async with page.expect_navigation(
        url=re.compile(r"kozazandaka"), wait_until="load", timeout=TIMEOUT
    ):
        await balance_button.click()

    log.info(f"Finding account info table element...")
    tables: List[Locator] = await page.locator("table.table-normal").all()

    return tables


async def parse_accounts_summary(tables: List[Locator]) -> pd.DataFrame:
    """
    Post-processing of the table html
    :param tables: The WebElement inputs of the accounts data from the site
    :return: A pandas dataframe of the downloaded data
    """
    table_dfs: List[pd.DataFrame] = list()
    for table in tables:
        # Create a simple dataframe from the input amount
        html: str = await table.evaluate("el => el.outerHTML")
        df: pd.DataFrame = pd.read_html(StringIO(str(html)))[0]

        # Remove non-numeric, non-decimal characters
        df["Account Number"]: pd.DataFrame = df["Account Number"].replace(
            to_replace=r"[^0-9\.]+", value="", regex=True
        )
        df["Available Amount"]: pd.DataFrame = df["Available Amount"].replace(
            to_replace=r"[^0-9\.]+", value="", regex=True
        )

        # Int-ify the monthly payment amount column
        df["Account Number"]: pd.DataFrame = df["Account Number"].apply(
            pd.to_numeric, errors="coerce"
        )
        df["Available Amount"]: pd.DataFrame = df["Available Amount"].apply(
            pd.to_numeric, errors="coerce"
        )

        # Drop unnamed columns
        df: pd.DataFrame = df.loc[:, ~df.columns.str.contains("^Unnamed")]

        # Drop columns where all values are null
        df: pd.DataFrame = df.dropna(axis=1, how="all")

        df["account_type"]: pd.DataFrame = "deposit"
        df["usd_value"]: pd.DataFrame = df["Currency"].map(get_usd_rate)

        table_dfs.append(df)

    return_df: pd.DataFrame = pd.concat(table_dfs)

    # Return the dataframe
    return return_df


async def run(
    playwright: Playwright, username: str, password: str, prometheus: bool = False
) -> Union[List[pd.DataFrame], Tuple[List[PrometheusMetric], List[PrometheusMetric]]]:
    """
    Gets the accounts info for a given user/pass as a list of pandas dataframes
    :param playwright: The playwright object for running this script
    :param username: Your username for logging in
    :param password: Your password for logging in
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
    await logon(page, username, password)

    # Navigate the site and download the accounts data
    accounts_data: List[Locator] = await seek_accounts_data(page)
    accounts_data_df: pd.DataFrame = await parse_accounts_summary(accounts_data)

    # Process tables
    return_tables: List[pd.DataFrame] = [accounts_data_df]

    # Convert to Prometheus exposition if flag is set
    if prometheus:
        balances: List[PrometheusMetric] = convert_to_prometheus(
            return_tables,
            INSTITUTION,
            "Account Number",
            "Currency",
            "Available Amount",
            "account_type",
        )

        asset_values: List[PrometheusMetric] = convert_to_prometheus(
            return_tables,
            INSTITUTION,
            "Account Number",
            "Currency",
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
    username: str, password: str, prometheus: bool = False
) -> Union[List[pd.DataFrame], Tuple[List[PrometheusMetric], List[PrometheusMetric]]]:
    """
    Gets the accounts info for a given user/pass as a list of pandas dataframes
    :param username: Your username for logging in
    :param password: Your password for logging in
    :param prometheus: True/False value for exporting as Prometheus-friendly exposition
    :return: A list of pandas dataframes of accounts info tables
    """
    # Instantiate the virtual display
    with Display(visible=False, size=(1280, 720)):
        async with async_playwright() as playwright:
            return await run(playwright, username, password, prometheus)
