"""
This file provides the get_accounts_info() function for RoundPoint Mortgage (https://www.roundpointmortgage.com/)

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
INSTITUTION: str = "RoundPoint Mortgage"
SYMBOL: str = "USD"

# Logon page
HOMEPAGE: str = (
    "https://loansphereservicingdigital.bkiconnect.com/servicinghome/#/login"
)
DASHBOARD_PAGE: str = (
    "https://loansphereservicingdigital.bkiconnect.com/servicinghome/#/dashboard"
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
    username_input: Locator = page.locator("input[id='username']")

    log.info(f"Sending info to username element...")
    log.debug(f"Username: {username}")
    await username_input.press_sequentially(username, delay=100)

    # Enter Password
    log.info(f"Finding password element...")
    password_input: Locator = page.locator("input[id='password']")

    log.info(f"Sending info to password element...")
    await password_input.press_sequentially(password, delay=100)

    # TOS
    log.info(f"Finding TOS element...")

    # Waiting for clickable doesn't trigger here
    tos: Locator = page.locator("input[id='agreeToTerms-input']")

    log.info(f"Clicking TOS element...")
    await tos.click()

    # Submit credentials
    log.info(f"Finding submit button element...")
    submit_button: Locator = page.locator("button")

    log.info(f"Clicking submit button element...")
    await submit_button.click()


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def wait_for_redirect(page: Page) -> None:
    """
    Wait for the page to redirect to the next stage of the login process
    :param page: The browser application
    """
    target_text: re.Pattern = re.compile(r"(Verify your account|Dashboard)")
    await expect(page.get_by_text(target_text).first).to_be_visible(timeout=TIMEOUT)


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def is_mfa_redirect(page: Page) -> bool:
    """
    Checks and determines if the site is forcing MFA on the login attempt
    :param page: The browser application
    :return: True if MFA is being enforced
    """
    return await page.get_by_text("Verify your account").is_visible()


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
    contact_options: List[Locator] = await page.locator(
        "bki-one-time-pin-verify input[type='radio']"
    ).all()

    log.info(f"Finding labels for contact options elements...")
    contact_options_text: List[Locator] = await page.locator(
        "bki-one-time-pin-verify label[class='mdc-label']"
    ).all()

    # Assertions
    assert len(contact_options) > 0
    assert len(contact_options) == len(contact_options_text)

    # Prompt user input for MFA option
    if mfa_auth is None:
        log.info(f"No automation info provided. Prompting user for contact option.")
        for i, l in enumerate(contact_options_text):
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
    log.info(f"Finding submit button element...")
    next_button: Locator = page.locator("bki-one-time-pin-verify button[type='submit']")

    log.info(f"Clicking submit button element...")
    await next_button.click()

    # Prompt user for OTP code and enter onto the page
    log.info(f"Finding input box element for OTP...")
    otp_input: Locator = page.locator("bki-one-time-pin-verify input[name='otpInput']")

    if mfa_auth is None:
        log.info(f"No automation info provided. Prompting user for OTP.")
        otp_code: str = input("Enter OTP Code: ")
    else:
        log.info(
            f"OTP file location found in automation info: {mfa_auth["otp_code_location"]}"
        )
        otp_code: str = search_files_for_int(
            mfa_auth["otp_code_location"],
            "Servicing Digital",
            6,
            10,
            TIMEOUT,
            reverse=True,
        )

    log.info(f"Sending info to OTP input box element...")
    await otp_input.press_sequentially(otp_code, delay=100)

    # Click submit once it becomes clickable
    log.info(f"Finding submit button element...")
    submit_button: Locator = page.locator(
        "bki-one-time-pin-verify button[type='submit']"
    )

    log.info(f"Clicking submit button element...")
    await submit_button.click()

    log.info(f"Finding close prompt button element...")
    close_button: Locator = page.locator(
        "bki-one-time-pin-verify button[type='submit']"
    )

    log.info(f"Clicking close prompt button element...")
    async with page.expect_navigation(
        url=re.compile(r"/dashboard"), wait_until="load", timeout=TIMEOUT
    ):
        await close_button.click()


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def seek_accounts_data(page: Page) -> str:
    """
    Navigate the website and click download button for the accounts data
    :param page: The Chrome browser application
    """
    log.info(f"Finding loan amount element...")
    amount_locator: Locator = page.get_by_role("heading", name="Loan balance").locator(
        ".amount"
    )
    amount: str = await amount_locator.text_content()
    return amount


def parse_accounts_summary(amount: str) -> pd.DataFrame:
    """
    Post-processing of the downloaded file removing disclaimers and other irrelevant mumbo jumbo
    :param amount: The total amount value of the account taken from the RoundPoint website
    :return: A pandas dataframe of the downloaded data
    """
    # Create a simple dataframe from the input amount
    df: pd.DataFrame = pd.DataFrame(data={"Balance": [str(amount)]})

    # Int-ify the monthly payment amount column
    df: pd.DataFrame = df.replace(to_replace=r"[^0-9\.]+", value="", regex=True)

    # Drop columns where all values are null
    df: pd.DataFrame = df.dropna(axis=1, how="all")

    # Return the dataframe
    return df


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def seek_other_data(page: Page) -> Tuple[List[Locator], List[Locator]]:
    """
    Navigate the website and click download button for the accounts data
    :param page: The Chrome browser application
    """
    log.info(f"Finding column headers elements...")
    keys: List[Locator] = await page.locator(
        "bki-dashboard-payment div[class='col']"
    ).all()

    log.info(f"Finding column values elements...")
    values: List[Locator] = await page.locator(
        "bki-dashboard-payment div[class='col strong']"
    ).all()

    return keys, values


async def parse_other_data(keys: List[Locator], values: List[Locator]) -> pd.DataFrame:
    """
    Parses other loan data, such as monthly payment info, from the RoundPoint site
    :param keys: A list of column headers as web elements. Acts as the left table in a left join
    :param values: A list of column values as web elements
    :return: A pandas dataframe of the data in the table
    """
    # Set up a dict for the df to read
    tbl: Dict = {}
    for i in range(len(keys)):
        key_text_content: str = str()
        while len(key_text_content) == 0:
            key_text_content: str = await keys[i].text_content()

        value_text_content: str = str()
        while len(value_text_content) == 0:
            value_text_content: str = await values[i].text_content()

        tbl[key_text_content.replace(":", "")] = [value_text_content]

    # Create the df
    df: pd.DataFrame = pd.DataFrame(data=tbl)

    # Int-ify the monthly payment amount column
    df["Monthly Payment Amount"] = df["Monthly Payment Amount"].replace(
        to_replace=r"[^0-9\.\/]+", value="", regex=True
    )

    # Drop columns where all values are null
    df: pd.DataFrame = df.dropna(axis=1, how="all")

    # Return the df
    return df


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def get_loan_number(page: Page) -> str:
    """
    Gets the full loan number from the My Loan page on the RoundPoint website
    :param page: The Chrome browser application
    :return: The full loan number as a string
    """
    # Navigate to the My Loan page
    log.info(
        f"Accessing: https://loansphereservicingdigital.bkiconnect.com/servicinghome/#/my-loan"
    )
    await page.goto(
        "https://loansphereservicingdigital.bkiconnect.com/servicinghome/#/my-loan",
        timeout=TIMEOUT,
        wait_until="load",
    )

    # Find the element for the loan number
    log.info(f"Finding loan number element...")
    loan_number_element: Locator = page.locator(
        "bki-myloan-balance a[class='card-link'][role='button']"
    )

    # Click so that the full loan number is exposed
    log.info(f"Clicking loan number element...")
    await loan_number_element.click()

    # Get the loan number
    log.info(f"Finding full loan number element...")
    loan_number: str = await page.locator(
        "bki-myloan-balance span[isolate='']"
    ).text_content()

    # Return the loan number
    return loan_number


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def scrape_loan_data(page: Page) -> List[pd.DataFrame]:
    """
    Iterates through the account's loans and processes the data into a list of Pandas DataFrames
    :param page: The Chrome browser application
    :return: A list of Pandas DataFrames containing the loans data
    """
    # Find and expand the dropdown list containing the account's loans
    log.info(f"Finding loans button dropdown element...")
    loans_button: Locator = page.locator("div[class='secondary-header-top'] button")

    log.info(f"Clicking loans button dropdown element...")
    await loans_button.click()

    # Get the list of loans in the dropdown list
    log.info(f"Finding loans button elements...")
    loans: List[Locator] = await page.locator("div[id='loanMenuId'] div.cursor").all()

    return_tables: List = list()
    for loan in loans:
        # Go back to dashboard page if not there already
        if page.url != DASHBOARD_PAGE:
            log.info(f"Accessing: {DASHBOARD_PAGE}")
            await page.goto(DASHBOARD_PAGE, timeout=TIMEOUT, wait_until="load")

        # Clicking to expand list...
        log.info(f"Clicking loans button dropdown element...")
        await loans_button.click()

        log.info(f"Clicking loans button dropdown element (again)...")
        await loans_button.click()

        log.info(f"Clicking loan button element...")
        await loan.click()

        # Navigate the site and get the loan amount
        amount: str = await seek_accounts_data(page)
        amount_df: pd.DataFrame = parse_accounts_summary(amount)

        # Get other details/info about the loan
        other_data_keys: List[Locator]
        other_data_values: List[Locator]
        other_data_keys, other_data_values = await seek_other_data(page)
        other_data_df: pd.DataFrame = await parse_other_data(
            other_data_keys, other_data_values
        )

        # Get the loan number
        loan_number: str = await get_loan_number(page)

        # Merge the loan amount and the other details
        return_table = pd.merge(
            amount_df, other_data_df, left_index=True, right_index=True
        )
        return_table["account_number"]: pd.DataFrame = loan_number
        return_table["account_type"]: pd.DataFrame = "loan"
        return_table["usd_value"]: pd.DataFrame = 1.0
        return_table["Balance"]: pd.DataFrame = pd.to_numeric(return_table["Balance"])

        return_tables.append(return_table)

    # Process tables
    return_table: pd.DataFrame = pd.concat(return_tables)
    return_table["symbol"]: pd.DataFrame = SYMBOL

    return_tables: List[pd.DataFrame] = [return_table]

    return return_tables


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
    page: Page = await browser.new_page()

    # Navigate to the logon page and submit credentials
    await logon(page, username, password)

    # Wait for landing page or MFA
    await wait_for_redirect(page)

    # Handle MFA if prompted, or quit if Chase catches us
    if await is_mfa_redirect(page):
        await handle_mfa_redirect(page, mfa_auth)

    # Scrape the loan data ready for output
    return_tables: List[pd.DataFrame] = await scrape_loan_data(page)

    # Convert to Prometheus exposition if flag is set
    if prometheus:
        balances: List[PrometheusMetric] = convert_to_prometheus(
            return_tables,
            INSTITUTION,
            "account_number",
            "symbol",
            "Balance",
            "account_type",
        )

        asset_values: List[PrometheusMetric] = convert_to_prometheus(
            return_tables,
            INSTITUTION,
            "account_number",
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
