"""
This file provides the get_accounts_info() function for Fidelity Net Benefits (https://nb.fidelity.com)

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
from typing import List, Tuple, Union
from datetime import datetime
from time import sleep
import os
import glob

# Non-Standard Imports
import pandas as pd
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
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
    wait_and_find_click_element,
    screenshot_on_timeout,
)
from bank_scrapers.scrapers.fidelity_netbenefits.mfa_auth import (
    FidelityNetBenefitsMfaAuth,
)

# Institution info
INSTITUTION: str = "Fidelity NetBenefits"
SYMBOL: str = "USD"

# Logon page
HOMEPAGE: str = (
    "https://login.fidelity.com/ftgw/Fas/Fidelity/NBPart/Login/Init?ISPBypass=true"
)
DASHBOARD_PAGE: str = "https://digital.fidelity.com/ftgw/digital/portfolio/positions"

# Timeout
TIMEOUT: int = 60

# Chrome config
USER_AGENT: str = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.50 Safari/537.36"
)
CHROME_OPTIONS: List[str] = [
    f"user-agent={USER_AGENT}",
    "--no-sandbox",
    "--window-size=1920,1080",
    "--disable-gpu",
    "--allow-running-insecure-content",
]

# Error screenshot config
ERROR_DIR: str = f"{ROOT_DIR}/errors"


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
def handle_multi_factor_authentication(
    driver: Chrome, wait: WebDriverWait, mfa_auth: FidelityNetBenefitsMfaAuth = None
) -> None:
    """
    Navigates the MFA workflow for this website
    Note that this function only covers Email Me options for now.
    :param driver: The Chrome driver/browser used for this function
    :param wait: The wait object associated with the driver function above
    :param mfa_auth: A typed dict containing an int representation of the MFA contact opt. and a dir containing the OTP
    """
    log.info(f"Redirected to two-factor authentication page.")

    log.info(f"Finding Text Me button element...")
    text_me_button_xpath: str = (
        "//pvd-button[@pvd-id='dom-channel-list-primary-button']"
    )
    text_me_button: WebElement = wait_and_find_element(
        driver, wait, (By.XPATH, text_me_button_xpath)
    )

    log.info(f"Clicking Text Me button element...")
    text_me_button.click()

    # Prompt user for OTP code and enter onto the page
    log.info(f"Finding input box element for OTP...")
    otp_input: WebElement = wait_and_find_element(
        driver, wait, (By.XPATH, "//input[@id='dom-otp-code-input']")
    )

    # Prompt user input for MFA option
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
                "NetBenefits",
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
        driver, wait, (By.XPATH, "//button[@id='dom-otp-code-submit-button']")
    )

    log.info(f"Clicking submit button element...")
    submit.click()


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
    log.info(f"Finding username element...")
    user: WebElement = wait_and_find_element(
        driver, wait, (By.XPATH, "//input[@id='dom-username-input']")
    )

    log.info(f"Sending info to username element...")
    log.debug(f"Username: {username}")
    user.send_keys(username)

    # Enter Password
    log.info(f"Finding password element...")
    passwd: WebElement = wait_and_find_element(
        driver, wait, (By.XPATH, "//input[@id='dom-pswd-input']")
    )

    log.info(f"Sending info to password element...")
    passwd.send_keys(password)

    # Submit
    log.info(f"Finding submit button element and waiting for it to be clickable...")
    submit: WebElement = wait_and_find_click_element(
        driver, wait, (By.XPATH, "//button[@id='dom-login-button']")
    )

    log.info(f"Clicking submit button element...")
    submit.click()

    # Wait for redirect to landing page or 2FA
    log.info(f"Waiting for redirect...")
    wait.until(
        lambda _: "https://workplaceservices.fidelity.com/" in driver.current_url
        or str("To verify it's you, we'll send a temporary code to your phone")
        in driver.page_source
    )


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
def seek_accounts_data(driver: Chrome, wait: WebDriverWait, tmp_dir: str) -> None:
    """
    Navigate the website and click download button for the accounts data
    :param driver: The Chrome browser application
    :param wait: WebDriverWait object for the driver
    :param tmp_dir: An empty directory to use for processing the downloaded file
    """
    # Go to the accounts page
    log.info(f"Accessing: {DASHBOARD_PAGE}")
    driver.get(DASHBOARD_PAGE)

    # Wait for the downloads button to be clickable
    log.info(f"Finding download button element...")
    download_btn: WebElement = wait_and_find_click_element(
        driver, wait, (By.XPATH, "//button[@aria-label='Download Positions']")
    )

    # Click the button
    log.info(f"Clicking download button element...")
    download_btn.click()

    # Allow the download to process
    while not glob.glob(os.path.join(tmp_dir, "Portfolio_Positions_*.csv")):
        log.info(f"Waiting for file: {tmp_dir}/Portfolio_Positions_*.csv")
        sleep(1)


def parse_accounts_summary(full_path: str) -> pd.DataFrame:
    """
    Post-processing of the downloaded file removing disclaimers and other irrelevant mumbo jumbo
    :param full_path: The path to the file to parse
    :return: A pandas dataframe of the downloaded data
    """
    df: pd.DataFrame = pd.read_csv(f"{full_path}", on_bad_lines="skip")
    df: pd.DataFrame = df[df["Account Name"].notna()]

    df["Quantity"]: pd.DataFrame = df["Quantity"].fillna(df["Current Value"])
    df["Quantity"]: pd.DataFrame = df["Quantity"].astype(str).str.replace("$", "")
    df["Quantity"]: pd.DataFrame = pd.to_numeric(df["Quantity"])

    df["Last Price"]: pd.DataFrame = df["Last Price"].fillna(1.0)
    df["Last Price"]: pd.DataFrame = df["Last Price"].astype(str).str.replace("$", "")
    df["Last Price"]: pd.DataFrame = pd.to_numeric(df["Last Price"])

    df["Symbol"]: pd.DataFrame = df["Symbol"].fillna(df["Description"])
    df["Symbol"]: pd.DataFrame = df["Symbol"].str.replace("FCASH**", "USD")

    return df


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
def is_mfa_redirect(driver: Chrome) -> bool:
    """
    Checks and determines if the site is forcing MFA on the login attempt
    :param driver: The browser application
    :return: True if MFA is being enforced
    """
    if (
        str("To verify it's you, we'll send a temporary code to your phone")
        in driver.page_source
    ):
        return True
    else:
        return False


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
def wait_for_landing_page(driver: Chrome, wait: WebDriverWait) -> None:
    """
    Wait for landing page after handling 2FA
    :param driver: The browser application
    :param wait: WebDriverWait object for the driver
    """
    log.info(f"Waiting for landing page...")
    wait.until(
        lambda _: "https://workplaceservices.fidelity.com/" in driver.current_url
    )


def get_accounts_info(
    username: str,
    password: str,
    tmp_dir: str,
    prometheus: bool = False,
    mfa_auth: FidelityNetBenefitsMfaAuth = None,
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
    display: Display = Display(visible=False, size=(800, 600))
    display.start()

    # Get Driver config
    options: ChromeOptions = get_chrome_options(CHROME_OPTIONS)

    # Instantiating the Driver
    driver: Chrome = start_chromedriver(options)
    wait: WebDriverWait = WebDriverWait(driver, TIMEOUT)

    enable_downloads(driver, downloads_dir=tmp_dir)

    # Navigate to the logon page and submit credentials
    logon(driver, wait, HOMEPAGE, username, password)

    # If 2FA...
    if is_mfa_redirect(driver):
        handle_multi_factor_authentication(driver, wait, mfa_auth)

    # Wait for redirect to landing page
    wait_for_landing_page(driver, wait)

    # Navigate the site and download the accounts data
    seek_accounts_data(driver, wait, tmp_dir)

    file_name: str = os.listdir(tmp_dir)[0]
    try:
        # Process tables
        return_tables: List[pd.DataFrame] = [
            parse_accounts_summary(f"{tmp_dir}/{file_name}")
        ]
        for t in return_tables:
            t["account_type"] = t.apply(
                lambda row: (
                    "deposit" if row["Account Number"].startswith("Z") else "retirement"
                ),
                axis=1,
            )
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
