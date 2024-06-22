"""
This file provides the get_accounts_info() function for SMBC Prestia (https://login.smbctb.co.jp)

Example Usage:
```
tables = get_accounts_info(username="{username}", password="{password}")
for t in tables:
    print(t.to_string())
```
"""

# Standard Library Imports
from typing import List, Tuple, Union
from io import StringIO
from datetime import datetime

# Non-Standard Imports
import pandas as pd
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from undetected_chromedriver import Chrome, ChromeOptions

# Local Imports
from bank_scrapers import ROOT_DIR
from bank_scrapers.common.functions import convert_to_prometheus, get_usd_rate
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

# Institution info
INSTITUTION: str = "SMBC Prestia"

# Logon page
HOMEPAGE: str = (
    "https://login.smbctb.co.jp/ib/portal/POSNIN1prestiatop.prst?LOCALE=en_JP"
)

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
    user: WebElement = wait_and_find_click_element(
        driver, wait, (By.XPATH, "//input[@id='dispuserId']")
    )

    log.info(f"Sending info to username element...")
    log.debug(f"Username: {username}")
    user.send_keys(username)

    # Enter Password
    log.info(f"Finding password element...")
    passwd: WebElement = wait_and_find_element(
        driver, wait, (By.XPATH, "//input[@id='disppassword']")
    )

    log.info(f"Sending info to password element...")
    passwd.send_keys(password)

    # Submit credentials
    log.info(f"Finding submit button element...")
    submit: WebElement = wait_and_find_element(driver, wait, (By.LINK_TEXT, "Sign On"))

    log.info(f"Clicking submit button element...")
    submit.click()


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
def seek_accounts_data(driver: Chrome, wait: WebDriverWait) -> List[WebElement]:
    """
    Navigate the website and find the accounts data for the user
    :param driver: The Chrome browser application
    :param wait: WebDriverWait object for the driver
    :return: The list of web elements of the accounts data
    """
    log.info(f"Finding accounts button element...")
    accounts_btn: WebElement = wait_and_find_click_element(
        driver, wait, (By.LINK_TEXT, "Accounts")
    )

    log.info(f"Clicking accounts button element...")
    accounts_btn.click()

    log.info(f"Finding balance button element...")
    balance_btn: WebElement = wait_and_find_click_element(
        driver, wait, (By.LINK_TEXT, "Balance Summary")
    )

    log.info(f"Clicking balance button element...")
    balance_btn.click()

    log.info(f"Finding account info table element...")
    tables: List[WebElement] = wait_and_find_elements(
        driver, wait, (By.XPATH, "//table[contains(@class, 'table-normal')]")
    )

    return tables


def parse_accounts_summary(tables: List[WebElement]) -> pd.DataFrame:
    """
    Post-processing of the table html
    :param tables: The WebElement inputs of the accounts data from the site
    :return: A pandas dataframe of the downloaded data
    """
    table_dfs: List[pd.DataFrame] = list()
    for table in tables:
        # Create a simple dataframe from the input amount
        html: str = table.get_attribute("outerHTML")
        df: pd.DataFrame = pd.read_html(StringIO(str(html)))[0]

        # Remove non-numeric, non-decimal characters
        df["Account Number"]: pd.DataFrame = df["Account Number"].replace(
            to_replace=r"[^0-9\.]+", value="", regex=True
        )
        df["Available Amount"]: pd.DataFrame = df["Available Amount"].replace(
            to_replace=r"[^0-9\.]+", value="", regex=True
        )

        # Int-ify the monthly payment amount column
        df["Account Number"]: pd.DataFrame = df["Account Number"].apply(
            pd.to_numeric, errors="coerce"
        )
        df["Available Amount"]: pd.DataFrame = df["Available Amount"].apply(
            pd.to_numeric, errors="coerce"
        )

        # Drop unnamed columns
        df: pd.DataFrame = df.loc[:, ~df.columns.str.contains("^Unnamed")]

        # Drop columns where all values are null
        df: pd.DataFrame = df.dropna(axis=1, how="all")

        df["account_type"]: pd.DataFrame = "deposit"
        df["usd_value"]: pd.DataFrame = df["Currency"].map(get_usd_rate)

        table_dfs.append(df)

    return_df: pd.DataFrame = pd.concat(table_dfs)

    # Return the dataframe
    return return_df


def get_accounts_info(
    username: str, password: str, prometheus: bool = False
) -> Union[List[pd.DataFrame], Tuple[List[PrometheusMetric], List[PrometheusMetric]]]:
    """
    Gets the accounts info for a given user/pass as a list of pandas dataframes
    :param username: Your username for logging in
    :param password: Your password for logging in
    :param prometheus: True/False value for exporting as Prometheus-friendly exposition
    :return: A list of pandas dataframes of accounts info tables
    """
    # Get Driver config
    chrome_options: ChromeOptions = get_chrome_options(CHROME_OPTIONS)

    # Instantiating the Driver
    driver: Chrome = start_chromedriver(chrome_options)
    wait: WebDriverWait = WebDriverWait(driver, TIMEOUT)

    # Navigate to the logon page and submit credentials
    logon(driver, wait, HOMEPAGE, username, password)

    # Navigate the site and download the accounts data
    accounts_data: List[WebElement] = seek_accounts_data(driver, wait)
    accounts_data_df: pd.DataFrame = parse_accounts_summary(accounts_data)

    # Process tables
    return_tables: List[pd.DataFrame] = [accounts_data_df]

    # Clean up
    driver.quit()

    # Convert to Prometheus exposition if flag is set
    if prometheus:
        balances: List[PrometheusMetric] = convert_to_prometheus(
            return_tables,
            INSTITUTION,
            "Account Number",
            "Currency",
            "Available Amount",
            "account_type",
        )

        asset_values: List[PrometheusMetric] = convert_to_prometheus(
            return_tables,
            INSTITUTION,
            "Account Number",
            "Currency",
            "usd_value",
            "account_type",
        )

        return_tables: Tuple[List[PrometheusMetric], List[PrometheusMetric]] = (
            balances,
            asset_values,
        )

    # Return list of pandas df
    return return_tables
