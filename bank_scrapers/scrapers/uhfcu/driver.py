"""
This file provides the get_accounts_info() function for UHFCU (https://online.uhfcu.com)

Example Usage:
```
tables = get_accounts_info(username="{username}", password="{password}")
for t in tables:
    print(t.to_string())
```
"""

# Standard Library Imports
from typing import List, Tuple, Dict, Union
from datetime import datetime
import time
import re

# Non-Standard Imports
import pandas as pd
from patchright.async_api import (
    async_playwright,
    Playwright,
    Page,
    Locator,
    expect,
    BrowserContext,
    TimeoutError as PlaywrightTimeoutError,
)
from pyvirtualdisplay import Display

# Local Imports
from bank_scrapers import ROOT_DIR
from bank_scrapers.common.functions import convert_to_prometheus, search_files_for_int
from bank_scrapers.common.log import log
from bank_scrapers.common.types import PrometheusMetric
from bank_scrapers.scrapers.common.browser import launch_context
from bank_scrapers.scrapers.common.functions import screenshot_on_timeout
from bank_scrapers.scrapers.common.mfa_auth import MfaAuth

# Institution info
INSTITUTION: str = "UHFCU"
SYMBOL: str = "USD"

# Logon page
HOMEPAGE: str = "https://online.uhfcu.com/sign-in?user=&SubmitNext=Sign%20On"

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
    :param homepage: The logon url to initially navigate
    :param username: Your username for logging in
    :param password: Your password for logging in
    """
    # Logon Page
    log.info(f"Accessing: {homepage}")
    await page.goto(homepage, timeout=TIMEOUT, wait_until="load")

    # Enter User
    log.info(f"Finding username element...")
    username_input: Locator = page.locator("input[id='username']")

    log.info(f"Sending info to username element...")
    log.debug(f"Username: {username}")
    loop_timeout: float = time.time() + (TIMEOUT / 1000)
    while not await username_input.input_value() == username:
        if time.time() > loop_timeout:
            raise PlaywrightTimeoutError
        await username_input.press_sequentially(username, delay=100)

    # Enter Password
    log.info(f"Finding password element...")
    password_input: Locator = page.locator("input[id='password']")

    log.info(f"Sending info to password element...")
    await password_input.press_sequentially(password, delay=100)

    # Submit will sometimes stay inactive unless interacted with
    log.info(f"Finding submit button element...")
    submit_button: Locator = page.locator("button[type='submit']")

    log.info(f"Clicking submit button element...")
    await submit_button.click()

    # Wait for redirect to landing page or MFA
    log.info(f"Waiting for redirect...")


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def wait_for_redirect(page: Page) -> None:
    """
    Wait for the page to redirect to the next stage of the login process
    :param page: The browser application
    """
    target_text: re.Pattern = re.compile(r"(Security Checks|Dashboard)")
    await expect(page.get_by_text(target_text)).not_to_have_count(0, timeout=TIMEOUT)


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def is_mfa_redirect(page: Page) -> bool:
    """
    Checks and determines if the site is forcing MFA on the login attempt
    :param page: The browser application
    :return: True if MFA is being enforced
    """
    return await page.get_by_text("Security Checks").is_visible()


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def handle_mfa_redirect(page: Page, mfa_auth: MfaAuth = None) -> None:
    """
    Navigates the MFA workflow for this website
    :param page: The Chrome page/browser used for this function
    :param mfa_auth: A typed dict containing an int representation of the MFA contact opt. and a dir containing the OTP
    """
    log.info(f"Redirected to multi-factor authentication page.")

    otp_input: Locator = (
        page.get_by_text("Security Checks").locator("..").locator("input")
    )

    # UHFCU now skips the contact-method picker when there's only one option:
    # it sends the SMS automatically and lands directly on the OTP-entry view.
    # Old flow still applies if the picker is shown.
    try:
        await otp_input.wait_for(state="visible", timeout=3000)
        log.info("OTP input visible immediately; skipping contact-method picker")
    except Exception:
        log.info("OTP input not visible; driving contact-method picker first")

        log.info("Finding contact options elements...")
        contact_options: List[Locator] = (
            await page.get_by_text("Security Checks")
            .locator("..")
            .locator(":enabled")
            .all()
        )

        if mfa_auth is None:
            for i, l in enumerate(contact_options):
                log.info("No automation info provided. Prompting user for contact option.")
                print(f"{i + 1}: {(await l.text_content()).replace('\n','')}")
            option: str = input("Please select one: ")
        else:
            log.info("Contact option found in automation info.")
            option: str = str(mfa_auth["otp_contact_option"])
        option_index: int = int(option) - 1
        log.debug(f"Contact option: {option_index}")

        log.info("Clicking element for user selected contact option...")
        await contact_options[option_index].click()

        log.info("Clicking 'Get Code' button...")
        await page.get_by_text("Get Code").click()

        log.info("Waiting for OTP input to appear...")
        await otp_input.wait_for(state="visible", timeout=TIMEOUT)

    if mfa_auth is None:
        log.info("No automation info provided. Prompting user for OTP.")
        otp_code: str = input("Enter OTP Code: ")
    else:
        log.info(
            f"OTP file location found in automation info: {mfa_auth["otp_code_location"]}"
        )
        otp_code: str = search_files_for_int(
            mfa_auth["otp_code_location"],
            "University of Hawaii Federal Credit Union",
            6,
            10,
            TIMEOUT,
            reverse=True,
        )

    log.info("Sending info to OTP input box element...")
    # UHFCU's Angular form keeps the OTP input readonly until focused as an
    # anti-autofill hack. Click the field so its onfocus handler removes the
    # attribute, then fill — Playwright refuses to fill readonly fields.
    await otp_input.click()
    await otp_input.fill(otp_code)

    log.info("Clicking Continue submit button...")
    submit_button: Locator = page.locator("button").get_by_text("Continue")
    async with page.expect_navigation(
        url=re.compile(r"/dashboard"), wait_until="load", timeout=TIMEOUT
    ):
        await submit_button.click(force=True)


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def get_accounts_tables(page: Page) -> List[Locator]:
    """
    Gets a WebElement for each account
    :param page: The browser application
    """
    # Process tables
    log.info(f"Finding accounts tables...")

    log.info("Waiting for accounts tables to be visible...")
    table_locator: Locator = page.locator("app-sub-accounts-tiles app-sub-account-card")
    await expect(table_locator).not_to_have_count(0, timeout=TIMEOUT)

    return await table_locator.all()


async def parse_accounts_summary(table: Locator) -> pd.DataFrame:
    """
    Takes a table as a web element from the UHFCU accounts overview page and turns it into a pandas df
    :param table: The table as a web element
    :return: A pandas dataframe of the table
    """
    # Data
    account_type: str = await table.locator("h4").text_content()
    account_desc: str = await table.get_by_text(re.compile("XXX")).text_content()

    # The remaining elements
    balance_infos: List[Locator] = (
        await table.locator("div.flex.flex-col")
        .locator("span.amount")
        .locator("..")
        .all()
    )

    # Data
    balance_dict: Dict = {
        "Account Type": account_type.strip(),
        "Account Desc": account_desc.strip(),
    }
    for info in balance_infos:
        # Append balance_dict
        key: str = await info.locator("span.text-xs").text_content()
        value: str = await info.locator("span.amount").text_content()
        balance_dict[key.strip()] = [value.strip()]

    # Make a df from the dict
    df: pd.DataFrame = pd.DataFrame(data=balance_dict)

    return df


def post_process_tables(
    deposit_table: pd.DataFrame, credit_table: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Cleans up data unnecessary substring and info contained in parsed accounts data
    :param deposit_table: The Pandas dataframe parsed from the deposit accounts data
    :param credit_table: The Pandas dataframe parsed from the credit accounts data
    :return: A tuple containing the cleaned up dataframes for both deposit and credit accounts
    """
    for table, account_type in [(deposit_table, "deposit"), (credit_table, "credit")]:
        table["symbol"]: pd.DataFrame = SYMBOL
        table["account_type"]: pd.DataFrame = account_type
        table["usd_value"]: pd.DataFrame = 1.0

        for col in ["Current Balance", "Pending Balance", "Available"]:
            if col in table.columns:
                table[col]: pd.DataFrame = table[col].replace(
                    to_replace=r"[^0-9\.]+", value="", regex=True
                )
                table[col]: pd.DataFrame = pd.to_numeric(table[col])

        # Both deposit and credit tiles render the description as
        # "<Account Holder> - XXX <account>"; keep only the masked account
        table["Account Desc"]: pd.DataFrame = table["Account Desc"].replace(
            to_replace=r".* - ", value="", regex=True
        )

    return deposit_table, credit_table


async def run(
    playwright: Playwright,
    username: str,
    password: str,
    prometheus: bool = False,
    mfa_auth: MfaAuth = None,
) -> Union[List[pd.DataFrame], Tuple[List[PrometheusMetric], List[PrometheusMetric]]]:
    """
    Gets the accounts info for a given user/pass as a list of pandas dataframes
    :param playwright: The playwright object for running this script
    :param username: Your username for logging in
    :param password: Your password for logging in
    :param prometheus: True/False value for exporting as Prometheus-friendly exposition
    :param mfa_auth: A typed dict containing an int representation of the MFA contact opt. and a dir containing the OTP
    :return: A list of pandas dataframes of accounts info tables
    """
    # Instantiate browser
    browser: BrowserContext = await launch_context(playwright, INSTITUTION)
    page: Page = await browser.new_page()

    # Navigate to the logon page and submit credentials
    await logon(page, username, password)

    # Wait for landing page or MFA
    await wait_for_redirect(page)

    # Handle MFA if prompted, or quit if Chase catches us
    if await is_mfa_redirect(page):
        await handle_mfa_redirect(page, mfa_auth)

    # Process tables
    tables: List[Locator] = await get_accounts_tables(page)
    deposit_tables: List = list()
    credit_tables: List = list()
    for t in tables:
        tile_text: str = await t.text_content()
        if "Share Account" in tile_text:
            deposit_tables.append(await parse_accounts_summary(t))
        elif "Loan Account" in tile_text:
            credit_tables.append(await parse_accounts_summary(t))

    deposit_table: pd.DataFrame = pd.concat(deposit_tables)
    credit_table: pd.DataFrame = pd.concat(credit_tables)

    deposit_table, credit_table = post_process_tables(deposit_table, credit_table)

    return_tables: List[pd.DataFrame] = [deposit_table, credit_table]

    # Convert to Prometheus exposition if flag is set
    if prometheus:
        balances: List[PrometheusMetric] = convert_to_prometheus(
            return_tables,
            INSTITUTION,
            "Account Desc",
            "symbol",
            "Current Balance",
            "account_type",
        )

        asset_values: List[PrometheusMetric] = convert_to_prometheus(
            return_tables,
            INSTITUTION,
            "Account Desc",
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
    mfa_auth: MfaAuth = None,
) -> Union[List[pd.DataFrame], Tuple[List[PrometheusMetric], List[PrometheusMetric]]]:
    """
    Gets the accounts info for a given user/pass as a list of pandas dataframes
    :param username: Your username for logging in
    :param password: Your password for logging in
    :param prometheus: True/False value for exporting as Prometheus-friendly exposition
    :param mfa_auth: A typed dict containing an int representation of the MFA contact opt. and a dir containing the OTP
    :return: A list of pandas dataframes of accounts info tables
    """
    # Instantiate the virtual display
    with Display(visible=False, size=(1280, 720)):
        async with async_playwright() as playwright:
            return await run(playwright, username, password, prometheus, mfa_auth)
