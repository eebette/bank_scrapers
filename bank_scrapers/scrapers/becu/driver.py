"""
This file provides the get_accounts_info() function for BECU (https://onlinebanking.becu.org)

Example Usage:
```
tables = get_accounts_info(username="{username}", password="{password}")
for t in tables:
    print(t.to_string())
```
"""

# Standard Library Imports
import asyncio
from typing import List, Tuple, Union
from datetime import datetime
from io import StringIO

# Non-Standard Imports
import pandas as pd
from undetected_playwright.async_api import (
    async_playwright,
    Playwright,
    Page,
    Locator,
    expect,
    Browser,
    BrowserContext,
)
from browserforge.fingerprints import FingerprintGenerator, Fingerprint
from browserforge.injectors.undetected_playwright import AsyncNewContext
from pyvirtualdisplay import Display

# Local Imports
from bank_scrapers import ROOT_DIR
from bank_scrapers.common.log import log
from bank_scrapers.common.types import PrometheusMetric
from bank_scrapers.common.functions import convert_to_prometheus
from bank_scrapers.scrapers.common.functions import screenshot_on_timeout

# Institution info
INSTITUTION: str = "BECU"
SYMBOL: str = "USD"

# Logon page
HOMEPAGE: str = "https://onlinebanking.becu.org/BECUBankingWeb/Login.aspx"

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
    username_input: Locator = page.locator("input[id='ctlSignon_txtUserID']")

    log.info(f"Sending info to username element...")
    await username_input.press_sequentially(username, delay=100)

    # Enter Password
    log.info(f"Finding password element...")
    password_input: Locator = page.locator("input[id='ctlSignon_txtPassword']")

    log.info(f"Sending info to password element...")
    await password_input.press_sequentially(password, delay=100)

    # Submit
    log.info(f"Finding submit button element...")
    submit_button: Locator = page.locator("input[id='ctlSignon_btnLogin']")

    log.info(f"Clicking submit button element...")
    await submit_button.click()


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def wait_for_redirect(page: Page) -> None:
    """
    Waits until the page redirects to account home, marketing/offer page, or MFA page
    :param page: The browser application
    """
    # Wait for redirect to landing page or marketing offer
    log.info(f"Handling redirect...")
    current_url: str = str()
    while "/Invitation/" not in current_url and "/Accounts/" not in current_url:
        await asyncio.sleep(1)
        current_url: str = page.url


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def is_marketing_redirect(page: Page) -> bool:
    """
    Checks and determines if the site is redirecting to a marketing offer on the login attempt
    :param page: The Chrome browser application
    :return: True if MFA is being enforced
    """
    if "/Invitation/" in page.url:
        return True
    else:
        return False


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def handle_marketing_redirect(page: Page) -> None:
    """
    Navigates the marketing page for this website and declines the offer
    :param page: The Chrome page/browser used for this function
    """
    log.info(f"Redirected to marketing offer page.")

    # Decline offer
    log.info(f"Finding decline button element...")
    decline_button: Locator = page.locator("button[name='ctlWorkflow$decline']")

    log.info(f"Clicking decline button element...")
    await decline_button.click()


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def wait_for_credit_details(page: Page) -> None:
    """
    Waits for the credit portion of the web page to load
    :param page: The Chrome page/browser used for this function
    """
    log.info(f"Waiting for credit details to render...")
    credit_details: Locator = page.locator(
        "xpath=//tbody[@id='visaTable']/tr[@class='item']"
    )
    await expect(credit_details).to_be_visible(timeout=TIMEOUT)


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def get_detail_tables(page: Page) -> List[Locator]:
    """
    Gets the web elements for the tables containing the account details for each account
    :param page: The browser application
    :return: A list containing the web elements for the tables
    """
    log.info(f"Finding accounts details elements...")
    tables_xpath: str = "//table[contains(@class, 'tablesaw-stack')]"
    tables: List[Locator] = await page.locator(f"xpath={tables_xpath}").all()
    return tables


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def process_table(table: Locator) -> pd.DataFrame:
    """
    Processes selenium table object into a pandas dataframe
    :param table: The selenium table object to be processed
    :return: A post-processed pandas dataframe of the original table object
    """
    # Get the html
    html: str = await table.evaluate("el => el.outerHTML")

    # Load into pandas
    df: pd.DataFrame = pd.read_html(StringIO(str(html)))[0]

    # Strip non-digit/decimal
    df: pd.DataFrame = df.replace(to_replace=r"[^0-9\.]+", value="", regex=True)

    # Drop the last row (totals) from the table
    df: pd.DataFrame = df.drop(df.tail(1).index)

    # Convert each column to numeric and nullify any non-cohesive data
    df: pd.DataFrame = df.apply(pd.to_numeric, errors="coerce")

    # Drop any columns where all values are null
    df: pd.DataFrame = df.dropna(axis=1, how="all")

    return df


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
    # Get fingerprint
    fingerprint: Fingerprint = FingerprintGenerator().generate(browser="chrome")

    # Instantiate browser
    browser: Browser = await playwright.chromium.launch(
        channel="chrome",
        headless=False,
        args=["--disable-blink-features=AutomationControlled"],
    )

    # Inject fingerprint
    context: BrowserContext = await AsyncNewContext(browser, fingerprint=fingerprint)
    page: Page = await context.new_page()

    # Logon to the site
    await logon(page, username, password)

    # Wait to be redirected to the next stage of the login process
    await wait_for_redirect(page)

    # Handle marketing page if presented
    if await is_marketing_redirect(page):
        await handle_marketing_redirect(page)

    # Get data for account and credit cards
    await wait_for_credit_details(page)
    tables: List[Locator] = await get_detail_tables(page)

    # Process tables
    return_tables: List = list()
    for t in tables:
        table: pd.DataFrame = await process_table(t)
        is_credit_account = any(
            list(True for header in table.columns if "credit" in header.lower())
        )
        table["account_type"]: pd.DataFrame = (
            "credit" if is_credit_account else "deposit"
        )
        table["symbol"]: pd.DataFrame = SYMBOL
        table["usd_value"]: pd.DataFrame = 1.0

        return_tables.append(table)

    # Clean up
    log.info("Closing page instance...")
    await page.close()

    # Convert to Prometheus exposition if flag is set
    if prometheus:
        balances: List[PrometheusMetric] = convert_to_prometheus(
            return_tables,
            INSTITUTION,
            "Account",
            "symbol",
            "Current Balance",
            "account_type",
        )

        asset_values: List[PrometheusMetric] = convert_to_prometheus(
            return_tables,
            INSTITUTION,
            "Account",
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
    username: str,
    password: str,
    prometheus: bool = False,
) -> Union[List[pd.DataFrame], Tuple[List[PrometheusMetric], List[PrometheusMetric]]]:
    """
    Gets the accounts info for a given user/pass as a list of pandas dataframes
    :param username: Your username for logging in
    :param password: Your password for logging in
    :param prometheus: True/False value for exporting as Prometheus-friendly exposition
    :return: A list of pandas dataframes of accounts info tables
    """
    # Instantiate the virtual display
    display: Display = Display(visible=False, size=(1280, 720))
    display.start()
    try:
        async with async_playwright() as playwright:
            return await run(playwright, username, password, prometheus)
    except Exception:
        display.stop()
        raise
