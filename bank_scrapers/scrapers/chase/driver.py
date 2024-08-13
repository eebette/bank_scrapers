"""
This file provides the get_accounts_info() function for Chase (https://www.chase.com)

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

# Non-standard Library Imports
import pandas as pd
from undetected_playwright.async_api import (
    async_playwright,
    Playwright,
    Page,
    Locator,
    Frame,
    expect,
    Browser,
)
from pyvirtualdisplay import Display

# Local Imports
from bank_scrapers import ROOT_DIR
from bank_scrapers.common.log import log
from bank_scrapers.common.types import PrometheusMetric
from bank_scrapers.common.functions import convert_to_prometheus, search_files_for_int
from bank_scrapers.scrapers.common.functions import screenshot_on_timeout
from bank_scrapers.scrapers.chase.mfa_auth import ChaseMfaAuth

# Institution info
INSTITUTION: str = "Chase"
SYMBOL: str = "USD"

# Logon page
HOMEPAGE: str = "https://www.chase.com/personal/credit-cards/login-account-access"

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

    # Navigate the login iframe
    log.info(f"Switching to iframe...")
    iframe: Frame = page.frame("routablecpologonbox")

    # Username
    log.info(f"Finding username element...")
    username_input: Locator = iframe.locator("input[id='userId-input']")

    log.info(f"Sending info to username element...")
    log.debug(f"Username: {username}")
    await username_input.press_sequentially(username, delay=100)

    # Password
    log.info(f"Finding password element...")
    password_input: Locator = iframe.locator("input[id='password-input']")

    log.info(f"Sending info to password element...")
    await password_input.press_sequentially(password, delay=100)

    # Submit
    log.info(f"Finding submit button element...")
    submit_button: Locator = iframe.locator("mds-button[id='signin-button']")

    log.info(f"Clicking submit button element...")
    async with page.expect_navigation(
        url=re.compile(r"/(auth|dashboard)/"), wait_until="load", timeout=TIMEOUT
    ):
        await submit_button.click(force=True)


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def wait_for_redirect(page: Page) -> None:
    """
    Wait for the page to redirect to the next stage of the login process
    :param page: The browser application
    """
    log.info("Waiting for auth page...")
    target_text: re.Pattern = re.compile(
        r"(Let's make sure it's you|We don't recognize this device)"
    )
    await expect(page.get_by_text(target_text)).to_be_visible(timeout=TIMEOUT)


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def is_mfa_redirect(page: Page) -> bool:
    """
    Checks and determines if the site is forcing MFA on the login attempt
    :param page: The browser application
    :return: True if MFA is being enforced
    """
    return await page.get_by_text("Let's make sure it's you").is_visible()


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def is_mfa_redirect_alternate(page: Page) -> bool:
    """
    Checks and determines if the site is forcing MFA on the login attempt
    :param page: The browser application
    :return: True if MFA is being enforced
    """
    return await page.get_by_text("We don't recognize this device").is_visible()


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def handle_mfa_redirect(page: Page, mfa_auth: ChaseMfaAuth = None) -> None:
    """
    Navigates the MFA workflow for this website
    Note that this function only covers Email Me options for now.
    :param page: The Chrome page/browser used for this function
    :param mfa_auth: A typed dict containing an int representation of the MFA contact opt. and a dir containing the OTP
    """
    log.info(f"Redirected to multi-factor authentication page.")

    # Identify MFA options
    log.info(f"Finding contact options elements...")
    contact_options_shadow_root: Locator = page.locator("mds-list[id='optionsList']")
    await expect(contact_options_shadow_root).to_be_visible(timeout=TIMEOUT)
    contact_options: List[Locator] = await contact_options_shadow_root.locator(
        "li"
    ).all()

    contact_options_text: List[str] = []
    for contact_option in contact_options:
        contact_option_element: Locator = contact_option.locator("label")
        contact_options_text.append(await contact_option_element.text_content())

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

    # Click based on user input
    log.info(f"Clicking element for user selected contact option...")
    await contact_options[option_index].click()

    # Open accounts dropdown
    log.info(f"Finding next button element...")
    next_button_shadow_root: Locator = page.locator("mds-button[id='next-content']")
    next_button: Locator = next_button_shadow_root.locator("button")

    log.info(f"Clicking next button element...")
    await next_button.click()

    # Prompt user for OTP code and enter onto the page
    log.info(f"Finding input box element for OTP...")
    otp_input_shadow_root: Locator = page.locator("mds-text-input-secure")
    otp_input: Locator = otp_input_shadow_root.locator("input[id='otpInput-input']")

    # Prompt user input for MFA option
    if mfa_auth is None:
        log.info(f"No automation info provided. Prompting user for OTP.")
        otp_code: str = input("Enter OTP Code: ")
    else:
        log.info(
            f"OTP file location found in automation info: {mfa_auth["otp_code_location"]}"
        )
        otp_code: str = search_files_for_int(
            mfa_auth["otp_code_location"], INSTITUTION, 6, 10, TIMEOUT, reverse=True
        )

    log.info(f"Sending info to OTP input box element...")
    await otp_input.press_sequentially(otp_code, delay=100)

    # Click submit once it becomes clickable
    log.info(f"Finding submit button element...")
    submit_button_shadow_root: Locator = page.locator("mds-button[id='next-content']")
    submit_button: Locator = submit_button_shadow_root.locator("button")

    log.info(f"Clicking submit button element...")
    await submit_button.click()


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def handle_mfa_redirect_alternate(
    page: Page, password: str, mfa_auth: ChaseMfaAuth = None
) -> None:
    """
    Navigates the MFA workflow for this website
    Note that this function only covers Email Me options for now.
    :param page: The Chrome page/browser used for this function
    :param password: User's password to enter along with OTP
    :param mfa_auth: A typed dict containing an int representation of the MFA contact opt. and a dir containing the OTP
    """
    log.info(f"Redirected to traditional multi-factor authentication page.")

    # Wait for the expand option to become clickable or else can lead to bugs where the list doesn't expand correctly
    log.info(
        f"Finding list expand button element and waiting for it to be clickable..."
    )
    expand_button: Locator = page.locator(
        "div[id='simplerAuth-dropdownoptions-styledselect']"
    )

    # Then click it
    log.info(f"Clicking list expand button element...")
    await expand_button.click()

    dropdown_locator: Locator = page.locator(
        "ul[id='ul-list-container-simplerAuth-dropdownoptions-styledselect']"
    )

    # Identify MFA options
    log.info(f"Waiting for contact options elements to be visible...")
    contact_options_locator: Locator = dropdown_locator.locator(
        "a.option:not([aria-disabled]):not([rel='Call'])"
    )

    # Click again if necessary
    while not await contact_options_locator.first.is_visible():
        await expand_button.click()

    await expect(contact_options_locator.first).to_be_visible(timeout=TIMEOUT)
    log.info("Getting contact options from dropdown...")
    contact_options_locators: List[Locator] = await contact_options_locator.all()
    contact_options: List[Tuple[Locator, str]] = list()
    for contact_option in contact_options_locators:
        contact_option_label_locator: Locator = contact_option.locator(
            "xpath=preceding::a[contains(@class, 'groupLabelContainer')][1]"
        )
        contact_option_text: str = await contact_option.text_content()
        contact_option_text: str = contact_option_text.strip()

        contact_option_label_text: str = (
            await contact_option_label_locator.text_content()
        )
        contact_option_label_text: str = contact_option_label_text.strip()

        contact_options.append(
            (contact_option, f"{contact_option_label_text}: {contact_option_text}")
        )

    # Prompt user input for MFA option
    if mfa_auth is None:
        log.info(f"No automation info provided. Prompting user for contact option.")
        for i, l in enumerate(contact_options):
            print(f"{i + 1}: {l[1]}")
        option: str = input("Please select one: ")
    else:
        log.info(f"Contact option found in automation info.")
        option: str = str(mfa_auth["otp_contact_option_alternate"])
    option_index: int = int(option) - 1
    log.debug(f"Contact option: {option_index}")

    # Click based on user input
    log.info(f"Clicking list expand button element...")
    if not await page.get_by_text(re.compile(r"(TEXT|CALL) ME")).first.is_visible():
        await expand_button.click()

    # Click again if necessary
    while not await contact_options[option_index][0].is_visible():
        await expand_button.click()

    log.info(f"Clicking element for user selected contact option...")
    await contact_options[option_index][0].click()

    # Click submit once it becomes clickable
    log.info(f"Finding submit button element and waiting for it to be clickable...")
    next_button: Locator = page.locator("button[id='requestIdentificationCode-sm']")

    log.info(f"Clicking submit button element...")
    await next_button.click()

    # Prompt user for OTP code and enter onto the page
    log.info(f"Finding input box element for OTP...")
    otp_input: Locator = page.locator("input[id='otpcode_input-input-field']")

    # Prompt user input for MFA option
    if mfa_auth is None:
        log.info(f"No automation info provided. Prompting user for OTP.")
        otp_code: str = input("Enter OTP Code: ")
    else:
        log.info(
            f"OTP file location found in automation info: {mfa_auth["otp_code_location"]}"
        )
        otp_code: str = search_files_for_int(
            mfa_auth["otp_code_location"], INSTITUTION, 6, 10, TIMEOUT, reverse=True
        )

    log.info(f"Sending info to OTP input box element...")
    await otp_input.press_sequentially(otp_code, delay=100)

    # Re-enter the password on the OTP page
    log.info(f"Finding password element...")
    password_input: Locator = page.locator("input[id='password_input-input-field']")

    log.info(f"Sending info to password element...")
    await password_input.press_sequentially(password, delay=100)

    # Click submit once it becomes clickable
    log.info(f"Finding submit button element...")
    submit_button: Locator = page.locator("button[id='log_on_to_landing_page-sm']")

    log.info(f"Clicking submit button element...")
    async with page.expect_navigation(
        url=re.compile(r"/dashboard/"), wait_until="load", timeout=TIMEOUT
    ):
        await submit_button.click()


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def seek_accounts_data(page: Page) -> None:
    """
    Navigate the website and click download button for the accounts data
    :param page: The Chrome browser application
    """
    # Navigate shadow root
    log.info(f"Finding shadow root for accounts dropdown element...")
    dropdown_shadow_root: Locator = page.locator("mds-button[text='More']")

    # Open accounts dropdown
    log.info(f"Finding accounts dropdown element...")
    dropdown: Locator = dropdown_shadow_root.locator("button")

    log.info(f"Clicking accounts dropdown element...")
    await dropdown.click()

    # Navigate another shadow root
    log.info(f"Finding shadow root for account details element...")
    account_details_shadow_root: Locator = dropdown_shadow_root.locator(
        "mds-menu-button-overlay"
    )

    # Wait for the account details button to be clickable and go to it
    log.info(f"Finding button for account details element...")
    account_details_button: Locator = account_details_shadow_root.locator(
        "button[aria-label='Account details']"
    )

    log.info(f"Clicking button for account details element...")
    await account_details_button.click()


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def get_account_number(page: Page) -> str:
    """
    Gets the account number from the credit card details page
    :param page: The browser application
    :return: A string containing the account number
    """
    log.info(f"Finding account number element...")
    account_number_xpath: str = (
        "//h2[contains(@class, 'accountdetails')]/span[contains(@class, 'mask-number')]"
    )
    account_number_element: Locator = page.locator(f"xpath={account_number_xpath}")
    account_number_text: str = await account_number_element.text_content()

    log.debug(f"Account number (raw): {account_number_text}")
    account_number: str = re.sub("[^0-9]", "", account_number_text)

    return account_number


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def get_detail_tables(page: Page) -> List[Locator]:
    """
    Gets the web elements for the tables containing the account details for each account
    :param page: The browser application
    :return: A list containing the web elements for the tables
    """
    log.info(f"Finding account details elements...")
    tables: List[Locator] = await page.locator(
        "xpath=//dl[contains(@class, 'details-bar')]"
    ).all()
    return tables


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
async def parse_accounts_summary(table: Locator) -> pd.DataFrame:
    """
    Takes a table as a web element from the Chase accounts overview page and turns it into a pandas df
    :param table: The table as a web element
    :return: A pandas dataframe of the table
    """
    # Transpose vertical headers labels
    dt_list: List[Locator] = await table.locator("xpath=.//dt").all()
    dt: List[str] = list()
    for d in dt_list:
        text_content: str = await d.text_content()
        if len(text_content) == 0:
            dt.append(await d.locator("span[class='link__text']").text_content())
        else:
            dt.append(text_content)

    # Data
    dd: List[str] = await table.locator("xpath=.//dd").all_inner_texts()

    # "zip" the data as a dict
    tbl: Dict = {}
    for i in range(len(dt)):
        tbl[dt[i]] = [dd[i]]

    # Make a df from the dict
    df: pd.DataFrame = pd.DataFrame(data=tbl)

    # Take out non-numbers/decimals
    df: pd.DataFrame = df.replace(to_replace=r"[^0-9\.]+", value="", regex=True)

    # Drop any all-null columns
    df: pd.DataFrame = df.dropna(axis=1, how="all")

    # Make sure that balance column is numeric
    if "Current balance" in df.columns:
        df["Current balance"]: pd.DataFrame = pd.to_numeric(df["Current balance"])

    return df


async def run(
    playwright: Playwright,
    username: str,
    password: str,
    prometheus: bool = False,
    mfa_auth: ChaseMfaAuth = None,
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

    if "auth" in page.url:
        await wait_for_redirect(page)

    # Handle MFA if prompted
    if await is_mfa_redirect(page):
        await handle_mfa_redirect(page, mfa_auth)

    # Handle MFA if prompted
    if await is_mfa_redirect_alternate(page):
        await handle_mfa_redirect_alternate(page, password, mfa_auth)

    # Navigate the site and download the accounts data
    await seek_accounts_data(page)

    # Get the account number from the current page
    account_number: str = await get_account_number(page)

    # Process tables
    tables: List[Locator] = await get_detail_tables(page)
    return_tables: List = list()
    for t in tables:
        parsed_table: pd.DataFrame = await parse_accounts_summary(t)
        parsed_table["account"]: pd.DataFrame = account_number
        parsed_table["account_type"]: pd.DataFrame = "credit"
        parsed_table["symbol"]: pd.DataFrame = SYMBOL
        if "Current balance" in parsed_table.columns:
            parsed_table["usd_value"]: pd.DataFrame = 1.0
        return_tables.append(parsed_table)

    # Clean up
    log.info("Closing page instance...")
    await page.close()

    # Convert to Prometheus exposition if flag is set
    if prometheus:
        balances: List[PrometheusMetric] = convert_to_prometheus(
            return_tables,
            INSTITUTION,
            "account",
            "symbol",
            "Current balance",
            "account_type",
        )

        asset_values: List[PrometheusMetric] = convert_to_prometheus(
            return_tables,
            INSTITUTION,
            "account",
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
    mfa_auth: ChaseMfaAuth = None,
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
