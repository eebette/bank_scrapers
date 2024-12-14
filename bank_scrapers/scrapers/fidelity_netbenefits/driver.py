"""
This file provides the get_accounts_info() function for Fidelity Net Benefits (https://nb.fidelity.com)

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
import os
from tempfile import TemporaryDirectory

# Non-Standard Imports
import pandas as pd
from undetected_playwright.async_api import (
    async_playwright,
    Playwright,
    Page,
    Locator,
    expect,
    Browser,
    Download,
)
from pyvirtualdisplay import Display

# Local Imports
from bank_scrapers import ROOT_DIR
from bank_scrapers.common.log import log
from bank_scrapers.common.types import PrometheusMetric
from bank_scrapers.common.functions import convert_to_prometheus, search_files_for_int
from bank_scrapers.scrapers.common.functions import screenshot_on_timeout
from bank_scrapers.scrapers.common.mfa_auth import MfaAuth


# Institution info
INSTITUTION: str = "Fidelity NetBenefits"
SYMBOL: str = "USD"

# Logon page
HOMEPAGE: str = "https://nb.fidelity.com/static/mybenefits/netbenefitslogin/#/login"
DASHBOARD_PAGE: str = "https://digital.fidelity.com/ftgw/digital/portfolio/positions"

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

    # Reject cookies if prompted
    reject_cookies_button: Locator = page.get_by_text("Reject All")
    if await reject_cookies_button.first.is_visible():
        log.info(f"Cookies button detected. Clicking Reject All button...")
        await reject_cookies_button.click()

    # Enter User
    log.info(f"Finding username element...")
    username_input: Locator = page.locator("input[id='dom-username-input']")

    log.info(f"Sending info to username element...")
    log.debug(f"Username: {username}")
    await username_input.fill(username)

    # Enter Password
    log.info(f"Finding password element...")
    await page.wait_for_selector("input[id='dom-pswd-input']")
    password_input: Locator = page.locator("input[id='dom-pswd-input']")

    log.info(f"Sending info to password element...")
    await password_input.fill(password)

    # Submit
    log.info(f"Finding submit button element...")
    submit_button: Locator = page.locator("button[id='dom-login-button']")

    log.info(f"Clicking submit button element...")
    await submit_button.click()


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def wait_for_redirect(page: Page) -> None:
    """
    Wait for the page to redirect to the next stage of the login process
    :param page: The browser application
    """
    target_text: re.Pattern = re.compile(
        r"(To verify it's you|Your accounts and benefits)"
    )
    await expect(page.get_by_text(target_text)).to_be_visible(timeout=TIMEOUT)


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def is_mfa_redirect(page: Page) -> bool:
    """
    Checks and determines if the site is forcing MFA on the login attempt
    :param page: The browser application
    :return: True if MFA is being enforced
    """
    return await page.get_by_text("To verify it's you").is_visible()


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def handle_mfa_redirect(page: Page, mfa_auth: MfaAuth = None) -> None:
    """
    Navigates the MFA workflow for this website
    Note that this function only covers Email Me options for now.
    :param page: The Chrome page/browser used for this function
    :param mfa_auth: A typed dict containing an int representation of the MFA contact opt. and a dir containing the OTP
    """
    log.info(f"Redirected to multi-factor authentication page.")

    # Reject cookies if prompted
    reject_cookies_button: Locator = page.get_by_text("Reject All")
    if await reject_cookies_button.first.is_visible():
        log.info(f"Cookies button detected. Clicking Reject All button...")
        await reject_cookies_button.click()

    log.info(f"Finding contact options elements...")
    await page.wait_for_selector("pvd-button")
    contact_options: List[Locator] = await page.locator("pvd-button").all()

    contact_options_text: List[str] = []
    for contact_option in contact_options:
        contact_option_text_element: Locator = contact_option.get_by_text(
            re.compile(r"(Text me|Call me)")
        )
        contact_options_text.append(await contact_option_text_element.text_content())

    # Prompt user input for MFA option
    if mfa_auth is None:
        log.info(f"No automation info provided. Prompting user for contact option.")
        for i, text in enumerate(contact_options_text):
            print(f"{i + 1}: {text}")
        option: str = input("Please select one: ")
    else:
        log.info(f"Contact option found in automation info.")
        option: str = str(mfa_auth["otp_contact_option"])
    option_index: int = int(option) - 1
    log.debug(f"Contact option: {option_index}")

    # Reject cookies if prompted
    reject_cookies_button: Locator = page.get_by_text("Reject All")
    if await reject_cookies_button.first.is_visible():
        log.info(f"Cookies button detected. Clicking Reject All button...")
        await reject_cookies_button.click()

    # Click based on user input
    log.info(f"Clicking element for user selected contact option...")
    await contact_options[option_index].click()

    # Prompt user for OTP code and enter onto the page
    log.info(f"Finding input box element for OTP...")
    otp_input: Locator = page.locator("input[id='dom-otp-code-input']")
    await expect(otp_input).to_be_editable(timeout=TIMEOUT)

    # Prompt user input for MFA option
    if mfa_auth is None:
        log.info(f"No automation info provided. Prompting user for OTP.")
        otp_code: str = input("Enter OTP Code: ")
    else:
        log.info(
            f"OTP file location found in automation info: {mfa_auth["otp_code_location"]}"
        )
        otp_code: str = search_files_for_int(
            mfa_auth["otp_code_location"], "NetBenefits", 6, 10, TIMEOUT, reverse=True
        )

    log.info(f"Sending info to OTP input box element...")
    await otp_input.press_sequentially(otp_code, delay=100)

    # Click submit once it becomes clickable
    log.info(f"Finding submit button element...")
    submit_button: Locator = page.locator("button[id='dom-otp-code-submit-button']")

    log.info(f"Clicking submit button element...")
    async with page.expect_navigation(
        url=re.compile(r"workplaceservices"), wait_until="load", timeout=TIMEOUT
    ):
        await submit_button.click(force=True)


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def seek_accounts_data(page: Page, tmp: str) -> None:
    """
    Navigate the website and click download button for the accounts data
    :param page: The Chrome browser application
    :param tmp: An empty directory to use for processing the downloaded file
    """
    # Go to the accounts page
    log.info(f"Accessing: {DASHBOARD_PAGE}")
    await page.goto(DASHBOARD_PAGE, timeout=TIMEOUT)

    # Wait for the kebab button to be clickable
    log.info(f"Finding download button element...")
    kebab_button: Locator = page.locator("#posweb-grid_top-kebab_popover-button button")
    download_button: Locator = page.locator("#kebabmenuitem-download")
    while not await download_button.is_visible():
        log.info(f"Clicking kebab button element...")
        await kebab_button.click()

    # Click the button
    log.info(f"Clicking download button element...")
    async with page.expect_download() as download_info:
        await download_button.click()
    download: Download = await download_info.value

    # Wait for the download process to complete and save the downloaded file
    await download.save_as(f"{tmp}/{download.suggested_filename}")


def parse_accounts_summary(full_path: str) -> pd.DataFrame:
    """
    Post-processing of the downloaded file removing disclaimers and other irrelevant mumbo jumbo
    :param full_path: The path to the file to parse
    :return: A pandas dataframe of the downloaded data
    """
    log.info(f"Opening file: {full_path}")
    df: pd.DataFrame = pd.read_csv(f"{full_path}", on_bad_lines="skip")

    log.info("Parsing data...")
    df: pd.DataFrame = df[df["Account Name"].notna()]
    df: pd.DataFrame = df[df["Current Value"].notna()]

    df["Quantity"]: pd.DataFrame = df["Quantity"].fillna(df["Current Value"])
    df["Quantity"]: pd.DataFrame = df["Quantity"].astype(str).str.replace("$", "")
    df["Quantity"]: pd.DataFrame = pd.to_numeric(df["Quantity"])

    df["Last Price"]: pd.DataFrame = df["Last Price"].fillna(1.0)
    df["Last Price"]: pd.DataFrame = df["Last Price"].astype(str).str.replace("$", "")
    df["Last Price"]: pd.DataFrame = pd.to_numeric(df["Last Price"])

    df["Symbol"]: pd.DataFrame = df["Symbol"].fillna(df["Description"])
    df["Symbol"]: pd.DataFrame = df["Symbol"].str.replace("FCASH**", "USD")

    return df


def get_account_type(row: pd.Series) -> str:
    """
    Returns whether the NetBenefits account number belongs to a deposit or retirement account
    :param row: The Pandas series containing the account number
    :return: String 'deposit' or 'retirement'
    """
    return "deposit" if row["Account Number"].startswith("Z") else "retirement"


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

    # Handle MFA if prompted
    if await is_mfa_redirect(page):
        await handle_mfa_redirect(page, mfa_auth)

    with TemporaryDirectory() as tmp:
        log.info(f"Created temporary directory: {tmp}")

        # Navigate the site and download the accounts data
        await seek_accounts_data(page, tmp)
        file_name: str = os.listdir(tmp)[0]

        # Process tables
        return_tables: List[pd.DataFrame] = [
            parse_accounts_summary(f"{tmp}/{file_name}")
        ]

    for t in return_tables:
        t["account_type"] = t.apply(lambda row: get_account_type(row), axis=1)

    # Convert to Prometheus exposition if flag is set
    if prometheus:
        balances: List[PrometheusMetric] = convert_to_prometheus(
            return_tables,
            INSTITUTION,
            "Account Number",
            "Symbol",
            "Quantity",
            "account_type",
        )

        asset_values: List[PrometheusMetric] = convert_to_prometheus(
            return_tables,
            INSTITUTION,
            "Account Number",
            "Symbol",
            "Last Price",
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
