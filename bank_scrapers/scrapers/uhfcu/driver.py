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

# Non-Standard Imports
import pandas as pd
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from undetected_chromedriver import Chrome, ChromeOptions

# Local Imports
from bank_scrapers import ROOT_DIR
from bank_scrapers.common.functions import convert_to_prometheus, search_files_for_int
from bank_scrapers.common.log import log
from bank_scrapers.common.types import PrometheusMetric
from bank_scrapers.scrapers.common.functions import (
    start_chromedriver,
    get_chrome_options,
    wait_and_find_element,
    wait_and_find_elements,
    wait_and_find_click_element,
    screenshot_on_timeout,
)
from bank_scrapers.scrapers.common.mfa_auth import MfaAuth


# Institution info
INSTITUTION: str = "UHFCU"
SYMBOL: str = "USD"

# Logon page
HOMEPAGE: str = "https://online.uhfcu.com/sign-in?user=&SubmitNext=Sign%20On"

# Timeout
TIMEOUT: int = 60

# Chrome config
CHROME_OPTIONS: List[str] = [
    "--no-sandbox",
    "--window-size=1920,1080",
    "--headless",
    "--disable-gpu",
    "--allow-running-insecure-content",
]

# Error screenshot config
ERROR_DIR: str = f"{ROOT_DIR}/errors"


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
def is_mfa_redirect(driver: Chrome) -> bool:
    """
    Checks and determines if the site is forcing MFA on the login attempt
    :param driver: The browser application
    :return: True if MFA is being enforced
    """
    if "Security Checks" in driver.page_source:
        return True
    else:
        return False


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
def handle_multi_factor_authentication(
    driver: Chrome, wait: WebDriverWait, mfa_auth: MfaAuth = None
) -> None:
    """
    Navigates the MFA workflow for this website
    :param driver: The Chrome driver/browser used for this function
    :param wait: The wait object associated with the driver function above
    :param mfa_auth: A typed dict containing an int representation of the MFA contact opt. and a dir containing the OTP
    """
    log.info(f"Redirected to two-factor authentication page.")

    # Find the MFA options presented by the app
    log.info(f"Finding MFA options elements...")
    options_buttons: List[WebElement] = wait_and_find_elements(
        driver,
        wait,
        (
            By.XPATH,
            "//h2[contains(text(), 'Security Checks')]/../button[not(@disabled)]",
        ),
    )

    # Prompt user input for MFA option
    if mfa_auth is None:
        for i, l in enumerate(options_buttons):
            log.info(f"No automation info provided. Prompting user for contact option.")
            print(f"{i+1}: {l.text}")
        option: str = input("Please select one: ")
    else:
        log.info(f"Contact option found in automation info.")
        option: str = str(mfa_auth["otp_contact_option"])
    l_index: int = int(option) - 1
    log.debug(f"Contact option: {l_index}")

    # Click based on user input
    log.info(f"Waiting for element for user selected contact option to be clickable...")
    mfa_option: WebElement = wait.until(
        EC.element_to_be_clickable(options_buttons[l_index])
    )

    log.info(f"Clicking element for user selected contact option...")
    mfa_option.click()

    # Click submit once it becomes clickable
    log.info(f"Finding submit button element and waiting for it to be clickable...")
    submit: WebElement = wait_and_find_click_element(
        driver, wait, (By.XPATH, "//button[contains(text(), 'Get Code')]")
    )

    log.info(f"Clicking submit button element...")
    submit.click()

    # Prompt user for OTP code and enter onto the page
    log.info(f"Finding input box element for OTP...")
    otp_input: WebElement = wait_and_find_element(
        driver, wait, (By.XPATH, "//h2[contains(text(), 'Security Checks')]/..//input")
    )
    if mfa_auth is None:
        log.info(f"No automation info provided. Prompting user for OTP.")
        otp_code: str = input("Enter OTP Code: ")
    else:
        log.info(
            f"OTP file location found in automation info: {mfa_auth["otp_code_location"]}"
        )
        otp_code: str = str(
            search_files_for_int(
                mfa_auth["otp_code_location"],
                "University of Hawaii Federal Credit Union",
                ".txt",
                6,
                10,
                TIMEOUT,
                True,
            )
        )

    log.info(f"Sending info to OTP input box element...")
    otp_input.send_keys(otp_code)

    # Click submit once it becomes clickable
    log.info(f"Finding submit button element and waiting for it to be clickable...")
    submit: WebElement = wait_and_find_click_element(
        driver,
        wait,
        (By.XPATH, "//mat-dialog-container//button[contains(text(), 'Sign In')]"),
    )

    log.info(f"Clicking submit button element...")
    submit.click()


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
def logon(
    driver: Chrome,
    wait: WebDriverWait,
    homepage: str,
    username: str,
    password: str,
) -> None:
    """
    Opens and signs on to an account
    :param driver: The browser application
    :param wait: WebDriverWait object for the driver
    :param homepage: The logon url to initially navigate
    :param username: Your username for logging in
    :param password: Your password for logging in
    """
    # Logon Page
    log.info(f"Accessing: {homepage}")
    driver.get(homepage)

    # Enter User
    log.info(f"Finding username element...")
    user: WebElement = wait_and_find_click_element(
        driver, wait, (By.XPATH, "//input[@id='username']")
    )

    log.info(f"Sending info to username element...")
    log.debug(f"Username: {username}")
    user.send_keys(username)

    # Enter Password
    log.info(f"Finding password element...")
    passwd: WebElement = wait_and_find_element(
        driver, wait, (By.XPATH, "//input[@id='password']")
    )

    log.info(f"Sending info to password element...")
    passwd.send_keys(password)

    # log.info(f"Sleeping for 2 seconds....")
    # sleep(2)

    # Submit will sometimes stay inactive unless interacted with
    log.info(f"Finding submit button element...")
    submit: WebElement = wait_and_find_click_element(
        driver, wait, (By.XPATH, "//button[@type='submit']")
    )

    log.info(f"Clicking submit button element...")
    submit.click()

    # Wait for redirect to landing page or MFA
    log.info(f"Waiting for redirect...")
    wait.until(
        lambda _: "https://online.uhfcu.com/consumer/main/dashboard"
        in driver.current_url
        or is_mfa_redirect(driver)
    )


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
def seek_credit_accounts_data(
    driver: Chrome, wait: WebDriverWait, table: WebElement
) -> None:
    """
    Navigate the website to get to the credit accounts details subpage
    :param driver: The Chrome browser application
    :param wait: WebDriverWait object for the driver
    :param table: The table on the dashboard which is being navigated for info
    """
    # Click into the credit card table
    log.info(f"Clicking into the credit card table...")
    table.click()

    # Navigate to the Manage Cards button on the page and click it
    log.info(f"Finding the Manage Cards button element...")
    manage_cards_btn: WebElement = wait_and_find_click_element(
        driver, wait, (By.XPATH, "//app-manage-cards//button")
    )

    log.info(f"Clicking the Manage Cards button element...")
    manage_cards_btn.click()

    # Wait for the new window or tab
    log.info(f"Waiting for new window...")
    wait.until(EC.number_of_windows_to_be(2))

    # Switch to the new window
    log.info(f"Switching to the Manage Cards window...")
    driver.switch_to.window(driver.window_handles[1])


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
def parse_credit_card_info(driver: Chrome, wait: WebDriverWait) -> pd.DataFrame:
    """
    Parses the info on the credit card accounts screen into a pandas df
    :param driver: The Chrome browser application
    :param wait: WebDriverWait object for the driver
    :return: A pandas dataframe of the credit card accounts data on the page
    """
    # Identify the account info rows on the screen
    log.info(f"Finding the credit card details table...")
    data_tbl: WebElement = wait_and_find_element(
        driver, wait, (By.XPATH, "//div[@class='module module-condensed'][1]")
    )

    # Pull each row as a newline separated kv pair
    data: List[WebElement] = wait_and_find_elements(
        data_tbl, wait, (By.XPATH, "//*[@class='text-underlined grid']")
    )
    data_txt: List[str] = list(i.text for i in data)

    # Split the kv pairs and enter into a dict
    data_dict: Dict = {}
    for d in data_txt:
        data_row = d.split("\n")
        data_dict[data_row[0]] = [data_row[-1]]

    # Make a df from the dict
    df: pd.DataFrame = pd.DataFrame(data=data_dict)

    account_details: WebElement = wait_and_find_element(
        driver, wait, (By.XPATH, "//li/span[text()='Account Details']/..")
    )
    account_details.click()

    account_number: str = wait_and_find_element(
        driver, wait, (By.XPATH, "//p[@id='AccountNumber']/span")
    ).text

    df["Account Desc"]: pd.DataFrame = account_number

    return df


def parse_accounts_summary(table: WebElement) -> pd.DataFrame:
    """
    Takes a table as a web element from the UHFCU accounts overview page and turns it into a pandas df
    :param table: The table as a web element
    :return: A pandas dataframe of the table
    """
    # Get a list of the card text
    account_info: List[str] = table.text.split(sep="\n")

    # Remove the first element (Share Account title)
    account_info.pop(0)

    # Data
    account_type: str = account_info.pop(0)
    account_desc: str = account_info.pop(0)

    # The remaining elements are alternating kv pairs as list elements, so split and zip
    balance_infos: zip = zip(
        list(e for i, e in enumerate(account_info) if i % 2 == 0),
        list(e for i, e in enumerate(account_info) if i % 2 != 0),
    )

    # Data
    balance_dict: Dict = {"Account Type": account_type, "Account Desc": account_desc}
    for info in balance_infos:
        # Append balance_dict with the tuple values zipped above
        balance_dict[info[0]] = [info[1]]

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
    deposit_table["symbol"]: pd.DataFrame = SYMBOL
    deposit_table["account_type"]: pd.DataFrame = "deposit"
    deposit_table["usd_value"]: pd.DataFrame = 1.0
    deposit_table["Current Balance"]: pd.DataFrame = deposit_table[
        "Current Balance"
    ].replace(to_replace=r"[^0-9\.]+", value="", regex=True)
    deposit_table["Current Balance"]: pd.DataFrame = pd.to_numeric(
        deposit_table["Current Balance"]
    )
    deposit_table["Account Desc"]: pd.DataFrame = deposit_table["Account Desc"].replace(
        to_replace=r".* - ", value="", regex=True
    )

    credit_table["symbol"]: pd.DataFrame = SYMBOL
    credit_table["account_type"]: pd.DataFrame = "credit"
    credit_table["usd_value"]: pd.DataFrame = 1.0
    credit_table["Current Balance"]: pd.DataFrame = credit_table[
        "Current Balance"
    ].replace(to_replace=r"[^0-9\.]+", value="", regex=True)
    credit_table["Current Balance"]: pd.DataFrame = pd.to_numeric(
        credit_table["Current Balance"]
    )
    credit_table["Account Desc"]: pd.DataFrame = credit_table["Account Desc"].replace(
        to_replace=r"[^0-9]+", value="", regex=True
    )

    return deposit_table, credit_table


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
def wait_for_landing_page(driver: Chrome, wait: WebDriverWait) -> None:
    """
    Wait for landing page after handling MFA
    :param driver: The browser application
    :param wait: WebDriverWait object for the driver
    """
    log.info(f"Waiting for landing page...")
    wait.until(
        lambda _: "https://online.uhfcu.com/consumer/main/dashboard"
        in driver.current_url
    )


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
def get_accounts_tables(driver: Chrome, wait: WebDriverWait) -> List[WebElement]:
    """
    Gets a WebElement for each account
    :param driver: The browser application
    :param wait: WebDriverWait object for the driver
    """
    # Process tables
    log.info(f"Finding accounts tables...")
    tables: List[WebElement] = wait_and_find_elements(
        driver, wait, (By.XPATH, "//app-sub-accounts-tiles//app-sub-account-card")
    )
    return tables


def get_accounts_info(
    username: str, password: str, prometheus: bool = False, mfa_auth: MfaAuth = None
) -> Union[List[pd.DataFrame], Tuple[List[PrometheusMetric], List[PrometheusMetric]]]:
    """
    Gets the accounts info for a given user/pass as a list of pandas dataframes
    :param username: Your username for logging in
    :param password: Your password for logging in
    :param prometheus: True/False value for exporting as Prometheus-friendly exposition
    :param mfa_auth: A typed dict containing an int representation of the MFA contact opt. and a dir containing the OTP
    :return: A list of pandas dataframes of accounts info tables
    """
    # Get Driver config
    chrome_options: ChromeOptions = get_chrome_options(CHROME_OPTIONS)

    # Instantiating the Driver
    driver: Chrome = start_chromedriver(chrome_options)
    wait: WebDriverWait = WebDriverWait(driver, TIMEOUT)

    # Navigate to the logon page and submit credentials
    logon(driver, wait, HOMEPAGE, username, password)

    # Handle MFA if prompted, or quit if Chase catches us
    if is_mfa_redirect(driver):
        handle_multi_factor_authentication(driver, wait, mfa_auth)

    # Wait for landing page after handling MFA
    wait_for_landing_page(driver, wait)

    # Process tables
    tables: List[WebElement] = get_accounts_tables(driver, wait)
    deposit_tables: List = list()
    credit_tables: List = list()
    for t in tables:
        if "Share Account" in t.text:
            deposit_tables.append(parse_accounts_summary(t))
        if "Loan Account" in t.text:
            seek_credit_accounts_data(driver, wait, t)
            credit_tables.append(parse_credit_card_info(driver, wait))

    deposit_table: pd.DataFrame = pd.concat(deposit_tables)
    credit_table: pd.DataFrame = pd.concat(credit_tables)

    deposit_table, credit_table = post_process_tables(deposit_table, credit_table)

    return_tables: List[pd.DataFrame] = [deposit_table, credit_table]

    # Clean up
    driver.quit()

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
