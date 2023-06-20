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

# Non-Standard Imports
import pandas as pd
from selenium.webdriver.common.by import By

# Local Imports
from bank_scrapers.scrapers.common.functions import *

# Logon page
HOMEPAGE: str = "https://login.smbctb.co.jp/ib/portal/POSNIN1prestiatop.prst?LOCALE=en_JP"

# Timeout
TIMEOUT: int = 15

# Chrome config
CHROME_OPTIONS: List[str] = [
    "--no-sandbox",
    "--window-size=1920,1080",
    "--headless",
    "--disable-gpu",
    "--allow-running-insecure-content",
]


def get_chrome_options(arguments: List[str]) -> ChromeOptions:
    """
    Returns Options object for a list of chrome options arguments
    :param arguments: A list of string-ified chrome arguments
    :return: Options object with chrome options set
    """
    chrome_options: ChromeOptions = ChromeOptions()
    for arg in arguments:
        chrome_options.add_argument(arg)

    return chrome_options


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


def parse_accounts_summary(table: WebElement) -> pd.DataFrame:
    """
    Post-processing of the table html
    :param table: The html input of the accounts data from the site
    :return: A pandas dataframe of the downloaded data
    """
    # Create a simple dataframe from the input amount
    html: str = table.get_attribute("outerHTML")
    df: pd.DataFrame = pd.read_html(html)[0]

    # Remove non-numeric, non-decimal characters
    df: pd.DataFrame = df.replace(to_replace=r"[^0-9\.]+", value="", regex=True)

    # Int-ify the monthly payment amount column
    df: pd.DataFrame = df.apply(pd.to_numeric, errors="coerce")

    # Drop columns where all values are null
    df.dropna(axis=1, how="all", inplace=True)

    # Return the dataframe
    return df


def get_accounts_info(username: str, password: str) -> List[pd.DataFrame]:
    """
    Gets the accounts info for a given user/pass as a list of pandas dataframes
    :param username: Your username for logging in
    :param password: Your password for logging in
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

    # Return list of pandas df
    return return_tables
