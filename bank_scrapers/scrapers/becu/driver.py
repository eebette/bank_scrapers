"""
This file provides the get_accounts_info() function for BECU (https://onlinebanking.becu.org)

Example Usage:
```
tables = get_accounts_info(username="{username}", password="{password}")
for t in tables:
    print(t.to_string())
```
"""
# Non-Standard Imports
import pandas as pd
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By

# Local Imports
from bank_scrapers.scrapers.common.functions import *

# Logon page
HOMEPAGE: str = "https://onlinebanking.becu.org/BECUBankingWeb/Login.aspx"

# Timeout
TIMEOUT: int = 10

# Chrome config
USER_AGENT: str = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.50 Safari/537.36"
CHROME_OPTIONS: List[str] = [
    f"user-agent={USER_AGENT}",
    "--no-sandbox",
    "--window-size=1920,1080",
    "--headless",
    "--disable-gpu",
    "--allow-running-insecure-content",
]


def get_chrome_options(arguments: List[str]) -> Options:
    """
    Returns Options object for a list of chrome options arguments
    :param arguments: A list of string-ified chrome arguments
    :return: Options object with chrome options set
    """
    chrome_options: Options = Options()
    for arg in arguments:
        chrome_options.add_argument(arg)
    return chrome_options


def process_table(table: WebElement) -> pd.DataFrame:
    """
    Processes selenium table object into a pandas dataframe
    :param table: The selenium table object to be processed
    :return: A post-processed pandas dataframe of the original table object
    """
    # Get the htmnl
    html: str = table.get_attribute("outerHTML")

    # Load into pandas
    table: pd.DataFrame = pd.read_html(html)[0]

    # Strip non-digit/decimal
    table: pd.DataFrame = table.replace(to_replace=r"[^0-9\.]+", value="", regex=True)

    # Drop the last row (totals) from the table
    table: pd.DataFrame = table.drop(table.tail(1).index)

    # Convert each column to numeric and nullify any non-cohesive data
    table: pd.DataFrame = table.apply(pd.to_numeric, errors="coerce")

    # Drop any columns where all values are null
    table: pd.DataFrame = table.dropna(axis=1, how="all")

    return table


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
    user: WebElement = wait_and_find_element(
        driver, wait, (By.ID, "ctlSignon_txtUserID")
    )
    user.send_keys(username)

    # Enter Password
    passwd: WebElement = wait_and_find_element(
        driver, wait, (By.ID, "ctlSignon_txtPassword")
    )
    passwd.send_keys(password)

    # Submit
    submit: WebElement = wait_and_find_element(
        driver, wait, (By.ID, "ctlSignon_btnLogin")
    )
    submit.click()

    # Wait for redirect to landing page
    wait.until(
        lambda driver: "https://onlinebanking.becu.org/BECUBankingWeb/Accounts/Summary.aspx"
        in driver.current_url
    )


def get_accounts_info(username: str, password: str) -> List[pd.DataFrame]:
    """
    Gets the accounts info for a given user/pass as a list of pandas dataframes
    :param username: Your username for logging in
    :param password: Your password for logging in
    :return: A list of pandas dataframes of accounts info tables
    """
    # Get Driver config
    chrome_options: Options = get_chrome_options(CHROME_OPTIONS)
    driver: Chrome = start_chromedriver(chrome_options)
    wait: WebDriverWait = WebDriverWait(driver, TIMEOUT)

    logon(driver, wait, HOMEPAGE, username, password)

    # Get data for account and credit cards
    tables: List[WebElement] = wait_and_find_elements(
        driver, wait, (By.CLASS_NAME, "tablesaw-stack")
    )

    # Process tables
    return_tables: List = list()
    for t in tables:
        table: pd.DataFrame = process_table(t)
        return_tables.append(table)

    # Clean up
    driver.quit()

    # Return list of pandas df
    return return_tables
