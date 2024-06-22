"""
This file provides the get_accounts_info() function for Vanguard (https://www.vanguard.com)

Example Usage:
```
from pathlib import Path
import random
r = list(str(r) for r in range(20))
random.shuffle(r)
seq = "".join(r)

tmp_dir = f"{Path.home()}/temp/bank_scraper_{seq}"
os.mkdir(tmp_dir)
tables = get_accounts_info(
    username="{username}", password="{password}", tmp_dir=tmp_dir
)
for t in tables:
    print(t.to_string())

import shutil
shutil.rmtree(tmp_dir)
```
"""

# Standard Library Imports
from typing import List, Tuple, Dict, Union
from datetime import datetime
from time import sleep
from random import randint
import os

# Non-Standard Imports
import pandas as pd
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from undetected_chromedriver import Chrome, ChromeOptions
from pyvirtualdisplay import Display

# Local Imports
from bank_scrapers import ROOT_DIR
from bank_scrapers.common.functions import convert_to_prometheus, search_files_for_int
from bank_scrapers.common.log import log
from bank_scrapers.common.types import PrometheusMetric
from bank_scrapers.scrapers.common.functions import (
    start_chromedriver,
    get_chrome_options,
    enable_downloads,
    wait_and_find_element,
    wait_and_find_elements,
    wait_and_find_click_element,
    screenshot_on_timeout,
)
from bank_scrapers.scrapers.common.mfa_auth import MfaAuth

# Institution info
INSTITUTION: str = "Vanguard"
SYMBOL: str = "USD"

# Logon page
HOMEPAGE = "https://logon.vanguard.com/logon"

# Timeout
TIMEOUT: int = 60

# Chrome config
CHROME_OPTIONS: List[str] = [
    "--no-sandbox",
    "--window-size=1920,1080",
    "--disable-gpu",
    "--allow-running-insecure-content",
]

# Error screenshot config
ERROR_DIR: str = f"{ROOT_DIR}/errors"


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

    # Select the mobile app MFA option
    log.info(f"Finding contact options elements...")
    mfa_buttons: List[WebElement] = wait_and_find_elements(
        driver, wait, (By.XPATH, "//lgn-auth-selection//button")
    )

    # Prompt user input for MFA option
    if mfa_auth is None:
        for i, l in enumerate(mfa_buttons):
            log.info(f"No automation info provided. Prompting user for contact option.")
            print(f"{i + 1}: {l.text}")
        o_index: int = int(input("Please select one: ")) - 1
    else:
        log.info(f"Contact option found in automation info.")
        o_index: int = mfa_auth["otp_contact_option"] - 1
    log.debug(f"Contact option: {o_index}")

    mfa_option: WebElement = mfa_buttons[o_index]
    mfa_option_text: str = mfa_buttons[o_index].text

    log.info(f"Clicking element for user selected contact option...")
    mfa_option.click()

    # Prompt user for MFA
    if "app" in mfa_option_text:
        print("Waiting for MFA...")
    else:
        log.info(f"Finding element for user selected contact option...")
        sms_button: WebElement = wait_and_find_element(
            driver, wait, (By.XPATH, "//lgn-phone-now-selection//button")
        )

        log.info(f"Clicking element for user selected contact option...")
        sms_button.click()

        log.info(f"Finding input box element for OTP...")
        otp: WebElement = wait_and_find_element(
            driver, wait, (By.XPATH, "//input[@id='CODE']")
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
                    "Vanguard",
                    ".txt",
                    6,
                    10,
                    TIMEOUT,
                    True,
                    delay=30,
                )
            )

        log.info(f"Sending info to OTP input box element...")
        otp.send_keys(otp_code)

    log.info(f"Finding submit button element...")
    submit_button: WebElement = wait_and_find_element(
        driver, wait, (By.XPATH, "//button[@type='submit']")
    )

    log.info(f"Clicking submit button element...")
    submit_button.click()


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
def is_mfa_redirect(driver: Chrome) -> bool:
    """
    Checks and determines if the site is forcing MFA on the login attempt
    :param driver: The browser application
    :return: True if MFA is being enforced
    """
    if (
        driver.current_url == "https://logon.vanguard.com/logon"
        and str("We need to verify it's you") in driver.page_source
    ):
        return True
    else:
        return False


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
def logon(
    driver: Chrome, wait: WebDriverWait, homepage: str, username: str, password: str
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
    sleep(randint(1, 5))
    log.info(f"Finding username element...")
    user: WebElement = wait_and_find_click_element(
        driver, wait, (By.XPATH, "//input[@id='USER']")
    )

    log.info(f"Sending info to username element...")
    log.debug(f"Username: {username}")
    user.send_keys(username)

    # Enter Password
    sleep(randint(1, 5))
    log.info(f"Finding password element...")
    passwd: WebElement = wait_and_find_element(
        driver, wait, (By.XPATH, "//input[@id='PASSWORD-blocked']")
    )

    log.info(f"Sending info to password element...")
    passwd.send_keys(password)

    # Submit credentials
    sleep(randint(1, 5))
    log.info(f"Finding submit button element and waiting for it to be clickable...")
    submit: WebElement = wait_and_find_click_element(
        driver, wait, (By.XPATH, "//button[@id='username-password-submit-btn-1']")
    )

    log.info(f"Clicking submit button element...")
    submit.click()

    log.info(f"Waiting for redirect...")
    wait.until(
        lambda _: "https://dashboard.web.vanguard.com/" in driver.current_url
        or "https://challenges.web.vanguard.com/" in driver.current_url
        or is_mfa_redirect(driver)
    )


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
def seek_accounts_data(driver: Chrome, wait: WebDriverWait, tmp_dir: str) -> None:
    """
    Navigate the website and click download button for the accounts data
    :param driver: The Chrome browser application
    :param wait: WebDriverWait object for the driver
    :param tmp_dir: An empty directory to use for processing the downloaded file
    """
    # Go to Downloads Center
    log.info(
        f"Accessing: https://personal1.vanguard.com/ofu-open-fin-exchange-webapp/ofx-welcome"
    )
    driver.get(
        "https://personal1.vanguard.com/ofu-open-fin-exchange-webapp/ofx-welcome"
    )

    # Select CSV option for download formats
    log.info(f"Finding download options element and waiting for it to be clickable...")
    download_option: WebElement = wait_and_find_click_element(
        driver, wait, (By.XPATH, "//vui-select[@id='optionSelect']")
    )

    log.info(f"Clicking download button...")
    download_option.click()

    log.info(f"Finding CSV option button element and waiting for it to be clickable...")
    vui_option: WebElement = wait_and_find_click_element(
        driver, wait, (By.XPATH, "//vui-option/span[text()[contains(.,'CSV')]]/..")
    )

    log.info(f"Clicking CSV option button...")
    vui_option.click()

    # Select last 18 months for date range
    log.info(
        f"Finding date range options dropdown button element and waiting for it to be clickable..."
    )
    date_range: WebElement = wait_and_find_click_element(
        driver, wait, (By.XPATH, "//vui-select[@id='dateSelect']")
    )

    log.info(f"Clicking date range options dropdown button...")
    date_range.click()

    log.info(
        f"Finding '18 months' option button element and waiting for it to be clickable..."
    )
    vui_option_: WebElement = wait_and_find_click_element(
        driver,
        wait,
        (By.XPATH, "//vui-option/span[text()[contains(.,'18 months')]]/.."),
    )

    log.info(f"Clicking '18 months' option button...")
    vui_option_.click()

    # Select for all accounts
    log.info(f"Finding accounts checkbox element and waiting for it to be clickable...")
    mat_checkbox = wait_and_find_click_element(
        driver, wait, (By.XPATH, "//input[@id='mat-checkbox-1-input']")
    )

    log.info(f"Clicking accounts checkbox element...")
    mat_checkbox.click()

    # Submit download request
    log.info(f"Finding submit button element and waiting for it to be clickable...")
    submit: WebElement = wait_and_find_click_element(
        driver, wait, (By.XPATH, "//vui-button[@id='submitOFXDownload']")
    )

    log.info(f"Clicking submit button element...")
    submit.click()

    # Allow the download to process
    while not os.path.exists(f"{tmp_dir}/OfxDownload.csv"):
        log.info(f"Waiting for file: {tmp_dir}/OfxDownload.csv")
        sleep(1)


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


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
def get_account_types(driver: Chrome, wait: WebDriverWait) -> pd.DataFrame:
    """
    Gets the account numbers and types for each account
    :param driver: The Chrome browser application
    :param wait: WebDriverWait object for the driver
    :return: A Pandas DataFrame containing the account numbers and types
    """
    log.info(f"Finding account type elements...")
    account_labels: List[str] = list(
        e.text
        for e in wait_and_find_elements(
            driver, wait, (By.XPATH, "//a[@data-cy='account-name']/span")
        )
    )

    accounts: Dict[str, str] = {}
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


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
def wait_for_landing_page(driver: Chrome, wait: WebDriverWait) -> None:
    """
    Wait for landing page after handling MFA
    :param driver: The browser application
    :param wait: WebDriverWait object for the driver
    """
    log.info(f"Waiting for landing page...")
    wait.until(
        lambda _: "https://dashboard.web.vanguard.com/" in driver.current_url
        or "https://challenges.web.vanguard.com/" in driver.current_url
    )


def get_accounts_info(
    username: str,
    password: str,
    tmp_dir: str,
    prometheus: bool = False,
    mfa_auth: MfaAuth = None,
) -> Union[List[pd.DataFrame], Tuple[List[PrometheusMetric], List[PrometheusMetric]]]:
    """
    Gets the accounts info for a given user/pass as a list of pandas dataframes
    :param username: Your username for logging in
    :param password: Your password for logging in
    :param tmp_dir: An empty directory to use for processing the downloaded file
    :param prometheus: True/False value for exporting as Prometheus-friendly exposition
    :param mfa_auth: A typed dict containing an int representation of the MFA contact opt. and a dir containing the OTP
    :return: A list of pandas dataframes of accounts info tables
    """
    # Instantiate the virtual display
    # display: Display = Display(visible=False, size=(800, 600))
    # display.start()

    # Get Driver config
    chrome_options: ChromeOptions = get_chrome_options(CHROME_OPTIONS)

    # Instantiating the Driver
    driver: Chrome = start_chromedriver(chrome_options)
    enable_downloads(driver, downloads_dir=tmp_dir)
    wait: WebDriverWait = WebDriverWait(driver, TIMEOUT)

    # Navigate to the logon page and submit credentials
    logon(driver, wait, HOMEPAGE, username, password)

    # Handle MFA if prompted, or quit if Chase catches us
    if is_mfa_redirect(driver):
        handle_multi_factor_authentication(driver, wait, mfa_auth)

    # Wait for landing page after handling MFA
    wait_for_landing_page(driver, wait)

    # Get the account types while on the dashboard screen
    accounts_df: pd.DataFrame = get_account_types(driver, wait)

    # Navigate the site and download the accounts data
    seek_accounts_data(driver, wait, tmp_dir)

    file_name: str = os.listdir(tmp_dir)[0]
    try:
        # Process tables
        accounts_data: pd.DataFrame = parse_accounts_summary(f"{tmp_dir}/{file_name}")
        return_tables: List[pd.DataFrame] = [pd.merge(accounts_df, accounts_data)]
    except Exception as e:
        log.error(e)
        exit(1)
    finally:
        # Clean up
        driver.quit()
        os.remove(f"{tmp_dir}/{file_name}")

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
