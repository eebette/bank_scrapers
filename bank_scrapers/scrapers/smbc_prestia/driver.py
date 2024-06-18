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
from bank_scrapers.scrapers.common.functions import (
    start_chromedriver,
    get_chrome_options,
    wait_and_find_element,
    wait_and_find_click_element,
    screenshot_on_timeout,
)
from bank_scrapers.common.functions import convert_to_prometheus, get_usd_rate
from bank_scrapers.common.types import PrometheusMetric

# Institution info
INSTITUTION: str = "SMBC Prestia"
SYMBOL: str = "JPY"

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
    driver.get(homepage)

    # Enter User
    user: WebElement = wait_and_find_click_element(driver, wait, (By.ID, "dispuserId"))
    user.send_keys(username)

    # Enter Password
    passwd: WebElement = wait_and_find_element(driver, wait, (By.ID, "disppassword"))
    passwd.send_keys(password)

    # Submit credentials
    submit: WebElement = wait_and_find_element(driver, wait, (By.LINK_TEXT, "Sign On"))
    submit.click()


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
def seek_accounts_data(driver: Chrome, wait: WebDriverWait) -> WebElement:
    """
    Navigate the website and find the accounts data for the user
    :param driver: The Chrome browser application
    :param wait: WebDriverWait object for the driver
    :return: The web element of the accounts data
    """
    accounts_btn: WebElement = wait_and_find_click_element(
        driver, wait, (By.LINK_TEXT, "Accounts")
    )
    accounts_btn.click()

    balance_btn: WebElement = wait_and_find_click_element(
        driver, wait, (By.LINK_TEXT, "Balance Summary")
    )
    balance_btn.click()

    table: WebElement = driver.find_element(
        By.CSS_SELECTOR,
        "body > form:nth-child(2) > main > div > section > div.inner > table.table.table-normal",
    )

    return table


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
def parse_accounts_summary(table: WebElement) -> pd.DataFrame:
    """
    Post-processing of the table html
    :param table: The html input of the accounts data from the site
    :return: A pandas dataframe of the downloaded data
    """
    # Create a simple dataframe from the input amount
    html: str = table.get_attribute("outerHTML")
    df: pd.DataFrame = pd.read_html(StringIO(str(html)))[0]

    # Remove non-numeric, non-decimal characters
    df: pd.DataFrame = df.replace(to_replace=r"[^0-9\.]+", value="", regex=True)

    # Int-ify the monthly payment amount column
    df: pd.DataFrame = df.apply(pd.to_numeric, errors="coerce")

    # Drop columns where all values are null
    df: pd.DataFrame = df.dropna(axis=1, how="all")

    df["symbol"]: pd.DataFrame = SYMBOL
    df["account_type"]: pd.DataFrame = "deposit"
    df["usd_value"]: pd.DataFrame = get_usd_rate(SYMBOL)

    # Return the dataframe
    return df


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
    accounts_data: WebElement = seek_accounts_data(driver, wait)
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
            "symbol",
            "Available Amount",
            "account_type",
        )

        asset_values: List[PrometheusMetric] = convert_to_prometheus(
            return_tables,
            INSTITUTION,
            "Account Number",
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
