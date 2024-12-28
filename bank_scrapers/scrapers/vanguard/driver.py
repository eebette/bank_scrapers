"""
This file provides the get_accounts_info() function for Vanguard (https://www.vanguard.com)

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
import os
from tempfile import TemporaryDirectory
from time import sleep
from random import randint, uniform

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
from bank_scrapers.common.functions import convert_to_prometheus, search_files_for_int
from bank_scrapers.common.log import log
from bank_scrapers.common.types import PrometheusMetric
from bank_scrapers.scrapers.common.functions import screenshot_on_timeout
from bank_scrapers.scrapers.common.mfa_auth import MfaAuth

# Institution info
INSTITUTION: str = "Vanguard"
SYMBOL: str = "USD"

# Logon page
HOMEPAGE: str = "https://logon.vanguard.com/logon"
DASHBOARD_PAGE: str = (
    "https://personal1.vanguard.com/ofu-open-fin-exchange-webapp/ofx-welcome"
)

# Timeout
TIMEOUT: int = 60 * 1000
OTP_TIMEOUT: int = 1200 * 1000

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
    username_input: Locator = page.locator("input[id='USER']")

    log.info(f"Sending info to username element...")
    log.debug(f"Username: {username}")
    sleep(randint(1, 5))
    await username_input.press_sequentially(username, delay=randint(100, 500))
    await username_input.press("Tab")

    # Enter Password
    log.info(f"Finding password element...")
    password_input: Locator = page.locator("input[id='PASSWORD-blocked']")

    log.info(f"Sending info to password element...")
    sleep(randint(1, 5))
    await password_input.type(password, delay=randint(100, 500))

    # Submit credentials
    log.info(f"Finding submit button element...")
    submit_button: Locator = page.locator("button[id='username-password-submit-btn-1']")

    log.info(f"Clicking submit button element...")

    sleep(uniform(1, 3))
    await submit_button.click()


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def wait_for_redirect(page: Page) -> None:
    """
    Wait for the page to redirect to the next stage of the login process
    :param page: The browser application
    """
    target_text: re.Pattern = re.compile(r"(We need to verify it's you|Welcome back,)")
    await expect(page.get_by_text(target_text)).to_be_visible(timeout=TIMEOUT)


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def is_mfa_redirect(page: Page) -> bool:
    """
    Checks and determines if the site is forcing MFA on the login attempt
    :param page: The browser application
    :return: True if MFA is being enforced
    """
    return await page.get_by_text("We need to verify it's you").is_visible(
        timeout=TIMEOUT
    )


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def handle_mfa_redirect(page: Page, mfa_auth: MfaAuth = None) -> None:
    """
    Navigates the MFA workflow for this website
    :param page: The Chrome page/browser used for this function
    :param mfa_auth: A typed dict containing an int representation of the MFA contact opt. and a dir containing the OTP
    """
    log.info(f"Redirected to multi-factor authentication page.")

    # Select the mobile app MFA option
    log.info(f"Finding contact options elements...")
    contact_options: List[Locator] = await page.locator(
        "lgn-auth-selection button"
    ).all()

    contact_options_text: List[str] = []
    for contact_option in contact_options:
        contact_options_text.append(
            await contact_option.get_by_text("Verify with").text_content()
        )

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

    mfa_option_text: str = await contact_options[option_index].text_content()

    # Click based on user input
    log.info(f"Clicking element for user selected contact option...")
    await contact_options[option_index].click()

    # Prompt user for MFA
    if "app" in mfa_option_text:
        async with page.expect_navigation(
            url=re.compile(r"dashboard.web.vanguard.com"),
            wait_until="load",
            timeout=TIMEOUT,
        ):
            print("Waiting for MFA...")
            await contact_options[option_index].click()
    else:
        log.info(f"Finding element for send SMS...")
        sms_button: Locator = page.locator("lgn-phone-now-selection button")

        log.info(f"Clicking element for send SMS...")
        await sms_button.click()

        log.info(f"Finding input box element for OTP...")
        otp_input: Locator = page.locator("input[id='CODE']")
        if mfa_auth is None:
            log.info(f"No automation info provided. Prompting user for OTP.")
            otp_code: str = input("Enter OTP Code: ")
        else:
            log.info(
                f"OTP file location found in automation info: {mfa_auth["otp_code_location"]}"
            )
            otp_code: str = search_files_for_int(
                mfa_auth["otp_code_location"],
                "Vanguard",
                6,
                10,
                OTP_TIMEOUT,
                delay=60,
                reverse=True,
            )

        log.info(f"Sending info to OTP input box element...")
        await otp_input.press_sequentially(otp_code, delay=100)

        log.info(f"Finding submit button element...")
        submit_button: Locator = page.locator("button[type='submit']")

        log.info(f"Clicking submit button element...")
        async with page.expect_navigation(
            url=re.compile(
                r"(dashboard.web.vanguard.com|challenges.web.vanguard.com/holiday)"
            ),
            wait_until="load",
            timeout=TIMEOUT,
        ):
            await submit_button.click()


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def is_holiday_redirect(page: Page) -> bool:
    """
    Checks and determines if the site is redirecting to a holiday closure notice
    :param page: The browser application
    :return: True if the site is redirecting to a holiday closure notice
    """
    if "challenges.web.vanguard.com/holiday" in page.url:
        log.info("Redirected to holiday closure notice...")
        return True
    else:
        return False


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def navigate_to_dashboard(page: Page) -> None:
    """
    Navigates to the landing page dashboard
    :param page: The browser application
    """
    log.info("Navigating to dashboard page...")
    await page.goto("https://dashboard.web.vanguard.com/", timeout=TIMEOUT)


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def get_account_types(page: Page) -> pd.DataFrame:
    """
    Gets the account numbers and types for each account
    :param page: The Chrome browser application
    :return: A Pandas DataFrame containing the account numbers and types
    """
    log.info(f"Finding account type elements...")

    log.info("Waiting for accounts tables to be visible...")
    account_label_locator: Locator = page.locator("a.account-holdings-link")
    await expect(account_label_locator.first).to_be_visible(timeout=TIMEOUT)

    account_label_elements: List[Locator] = await account_label_locator.all()

    account_labels: List[str] = list()
    for account_label_element in account_label_elements:
        account_label_text_content: str = await account_label_element.text_content()
        account_labels.append(account_label_text_content.strip())

    accounts: Dict[str, str] = dict()
    for account in account_labels:
        account_split: List[str] = account.split(sep=" — ")[1:]
        accounts[account_split[1]] = (
            "retirement"
            if "IRA" in account_split[0] or "401(k)" in account_split[0]
            else "deposit"
        )

    accounts_df: pd.DataFrame = pd.DataFrame(
        accounts.items(), columns=["Account Number", "account_type"]
    )
    accounts_df["Account Number"]: pd.DataFrame = pd.to_numeric(
        accounts_df["Account Number"]
    )

    return accounts_df


async def navigate_download_page_legacy(page: Page) -> Locator:
    """
    Navigates the legacy dropdown list based accounts download page sometimes rendered by Vanguard
    :param page: The Chrome browser application
    :return: The submit button locator for submitting the download on the page
    """
    log.info("Detected legacy downloads page.")

    # Select CSV option for download formats
    download_format_dropdown: Locator = page.locator(
        "span[id='OfxDownloadForm:downloadOption']"
    )
    csv_option: Locator = page.locator("td[value='CSVFile']")

    while not await csv_option.is_visible():
        log.info(f"Clicking download format options dropdown button element...")
        await download_format_dropdown.click(force=True)

    log.info(f"Clicking CSV option...")
    await csv_option.click()

    # Select last 18 months for date range
    date_range_dropdown: Locator = page.locator(
        "a[id='OfxDownloadForm:ofxDateFilterSelectOneMenu_aTag']"
    )
    eighteen_months_option: Locator = page.locator("td[value='EIGHTEEN_MONTH']")

    while not await eighteen_months_option.is_visible():
        await date_range_dropdown.click(force=True)

    log.info(f"Clicking '18 months' option button...")
    await page.locator("td[value='EIGHTEEN_MONTH']").click()

    # Select for all accounts
    log.info(f"Finding accounts checkbox element...")
    accounts_checkbox: Locator = page.locator("input[aria-label='All accounts']")

    log.info(f"Clicking accounts checkbox element...")
    await accounts_checkbox.click()

    # Submit download request
    log.info(f"Finding submit button element...")
    submit_button: Locator = page.locator(
        "input[id='OfxDownloadForm:downloadButtonInput']"
    )

    return submit_button


async def navigate_download_page(page: Page) -> Locator:
    """
    Navigates the standard accounts download page sometimes rendered by Vanguard
    :param page: The Chrome browser application
    :return: The submit button locator for submitting the download on the page
    """
    # Select CSV option for download formats
    log.info(f"Finding CSV option radio element...")
    csv_radio: Locator = page.get_by_text("CSV").locator(
        "xpath=../preceding-sibling::input"
    )
    log.info(f"Clicking CSV option button...")
    await csv_radio.check(force=True)

    # Select last 18 months for date range
    log.info(f"Finding date range options dropdown button element...")
    date_range: Locator = page.locator("select[id='selectId']")

    log.info(f"Clicking '18 months' option button...")
    await date_range.select_option("18 months")

    # Select for all accounts
    log.info(f"Finding accounts checkbox element...")
    accounts_checkbox: Locator = page.locator("input[aria-label='checkAll']")

    log.info(f"Clicking accounts checkbox element...")
    await accounts_checkbox.click(force=True)

    # Submit download request
    log.info(f"Finding submit button element...")
    submit_button: Locator = page.locator("[id='submitOFXDownload']")

    return submit_button


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def seek_accounts_data(page: Page, tmp: str) -> None:
    """
    Navigate the website and click download button for the accounts data
    :param page: The Chrome browser application
    :param tmp: An empty directory to use for processing the downloaded file
    """
    # Go to Downloads Center
    log.info(f"Accessing: {DASHBOARD_PAGE}")
    await page.goto(DASHBOARD_PAGE, timeout=TIMEOUT)

    download_format_dropdown: Locator = page.locator(
        "span[id='OfxDownloadForm:downloadOption']"
    )
    if await download_format_dropdown.is_visible():
        submit_button: Locator = await navigate_download_page_legacy(page)

    else:
        submit_button: Locator = await navigate_download_page(page)

    log.info(f"Clicking submit button element...")
    async with page.expect_download() as download_info:
        await submit_button.click()
    download: Download = await download_info.value

    # Wait for the download process to complete and save the downloaded file
    await download.save_as(f"{tmp}/{download.suggested_filename}")


def parse_accounts_summary(full_path: str) -> pd.DataFrame:
    """
    Post-processing of the downloaded file removing disclaimers and other irrelevant mumbo jumbo
    :param full_path: The path to the file to parse
    :return: A pandas dataframe of the downloaded data
    """
    df: pd.DataFrame = pd.read_csv(f"{full_path}", on_bad_lines="skip")
    df: pd.DataFrame = df.dropna(axis=1, how="all")
    df["Share Price"]: pd.DataFrame = pd.to_numeric(df["Share Price"])
    df["Shares"]: pd.DataFrame = pd.to_numeric(df["Shares"])
    return df


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

    # Handle holiday closures notice
    if await is_holiday_redirect(page):
        await navigate_to_dashboard(page)

    # Get the account types while on the dashboard screen
    accounts_df: pd.DataFrame = await get_account_types(page)

    with TemporaryDirectory() as tmp:
        log.info(f"Created temporary directory: {tmp}")

        # Navigate the site and download the accounts data
        await seek_accounts_data(page, tmp)
        file_name: str = os.listdir(tmp)[0]

        # Process tables
        accounts_data: pd.DataFrame = parse_accounts_summary(f"{tmp}/{file_name}")

        return_tables: List[pd.DataFrame] = [pd.merge(accounts_df, accounts_data)]

    # Convert to Prometheus exposition if flag is set
    if prometheus:
        balances: List[PrometheusMetric] = convert_to_prometheus(
            return_tables,
            INSTITUTION,
            "Account Number",
            "Symbol",
            "Shares",
            "account_type",
        )

        asset_values: List[PrometheusMetric] = convert_to_prometheus(
            return_tables,
            INSTITUTION,
            "Account Number",
            "Symbol",
            "Share Price",
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
