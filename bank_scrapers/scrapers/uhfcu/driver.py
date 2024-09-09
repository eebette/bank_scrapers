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
from undetected_playwright.async_api import (
    async_playwright,
    Playwright,
    Page,
    Locator,
    expect,
    Browser,
    BrowserContext,
    TimeoutError as PlaywrightTimeoutError,
)
from pyvirtualdisplay import Display

# Local Imports
from bank_scrapers import ROOT_DIR
from bank_scrapers.common.functions import convert_to_prometheus, search_files_for_int
from bank_scrapers.common.log import log
from bank_scrapers.common.types import PrometheusMetric
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
    await expect(page.get_by_text(target_text).first).to_be_visible()


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

    # Identify MFA options
    log.info(f"Finding contact options elements...")
    contact_options: List[Locator] = (
        await page.get_by_text("Security Checks")
        .locator("..")
        .locator(":enabled")
        .all()
    )

    # Prompt user input for MFA option
    if mfa_auth is None:
        for i, l in enumerate(contact_options):
            log.info(f"No automation info provided. Prompting user for contact option.")
            print(f"{i + 1}: {await l.text_content()}")
        option: str = input("Please select one: ")
    else:
        log.info(f"Contact option found in automation info.")
        option: str = str(mfa_auth["otp_contact_option"])
    option_index: int = int(option) - 1
    log.debug(f"Contact option: {option_index}")

    # Click based on user input
    log.info(f"Clicking element for user selected contact option...")
    await contact_options[option_index].click()

    # Click submit once it becomes clickable
    log.info(f"Finding submit button element and waiting for it to be clickable...")
    next_button: Locator = page.get_by_text("Get Code")

    log.info(f"Clicking submit button element...")
    await next_button.click()

    # Prompt user for OTP code and enter onto the page
    log.info(f"Finding input box element for OTP...")
    otp_input: Locator = (
        page.get_by_text("Security Checks").locator("..").locator("input")
    )

    if mfa_auth is None:
        log.info(f"No automation info provided. Prompting user for OTP.")
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

    log.info(f"Sending info to OTP input box element...")
    await otp_input.fill(otp_code)

    # Click submit once it becomes clickable
    log.info(f"Finding submit button element...")
    submit_button: Locator = page.locator("button").get_by_text("Sign In")

    log.info(f"Clicking submit button element...")
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
    await expect(table_locator.first).to_be_visible(timeout=TIMEOUT)

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


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def navigate_to_credit_accounts_data(
    context: BrowserContext, page: Page, table: Locator
) -> Page:
    """
    Navigate the website to get to the credit accounts details subpage
    :param context: The Chrome browser application's context
    :param page: The Chrome browser page
    :param table: The table on the dashboard which is being navigated for info
    :return: A Page at the credit card info page
    """
    # Click into the credit card table
    log.info(f"Clicking into the credit card table...")
    await table.click()

    # Navigate to the Manage Cards button on the page and click it
    log.info(f"Finding the Manage Cards button element...")
    manage_cards_button: Locator = page.locator("app-manage-cards button")

    # Wait for the new window or tab
    async with context.expect_page() as credit_card_page:
        log.info(f"Clicking the Manage Cards button element...")
        await manage_cards_button.click()

    return await credit_card_page.value


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def parse_credit_card_info(page: Page) -> pd.DataFrame:
    """
    Parses the info on the credit card accounts screen into a pandas df
    :param page: The Chrome browser application
    :return: A pandas dataframe of the credit card accounts data on the page
    """
    # Identify the account info rows on the screen
    log.info(f"Finding the credit card details table...")
    await expect(
        page.locator("div[id='CurrentBalance'] div.module.module-condensed")
    ).to_be_visible(timeout=TIMEOUT)
    data_table: Locator = page.locator(
        "div[id='CurrentBalance'] div.module.module-condensed"
    )

    # Pull each row as a newline separated kv pair
    data: List[Locator] = await data_table.locator(".text-underlined.grid").all()

    # Split the kv pairs and enter into a dict
    data_dict: Dict = dict()
    for d in data:
        text_content: str = await d.text_content()
        value: str = await d.locator("span.always-right").text_content()

        label: str = re.sub(r"(\s*)" + re.escape(value), "", text_content)
        label: str = re.sub(r"Go to(.*)$", "", label)

        data_dict[label.strip()] = [value.strip()]

    # Make a df from the dict
    df: pd.DataFrame = pd.DataFrame(data=data_dict)

    account_details: Locator = page.get_by_text("Account Details").locator("..")
    await account_details.click()

    account_number: str = await page.locator(
        "p[id='AccountNumber'] span"
    ).text_content()

    df["Account Desc"]: pd.DataFrame = account_number

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
    for table in [deposit_table, credit_table]:
        table["symbol"]: pd.DataFrame = SYMBOL
        table["account_type"]: pd.DataFrame = "deposit"
        table["usd_value"]: pd.DataFrame = 1.0

        for col in ["Current Balance", "Pending Balance", "Available"]:
            if col in table.columns:
                table[col]: pd.DataFrame = table[col].replace(
                    to_replace=r"[^0-9\.]+", value="", regex=True
                )
                table[col]: pd.DataFrame = pd.to_numeric(table[col])

    deposit_table["Account Desc"]: pd.DataFrame = deposit_table["Account Desc"].replace(
        to_replace=r".* - ", value="", regex=True
    )

    credit_table["Account Desc"]: pd.DataFrame = credit_table["Account Desc"].replace(
        to_replace=r"[^0-9]+", value="", regex=True
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
    browser: Browser = await playwright.chromium.launch(
        channel="chrome",
        headless=False,
        args=["--disable-blink-features=AutomationControlled"],
    )
    context: BrowserContext = await browser.new_context()
    page: Page = await context.new_page()

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
        if "Share Account" in await t.text_content():
            deposit_tables.append(await parse_accounts_summary(t))
        elif "Loan Account" in await t.text_content():
            credit_card_page: Page = await navigate_to_credit_accounts_data(
                context, page, t
            )
            credit_tables.append(await parse_credit_card_info(credit_card_page))

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
