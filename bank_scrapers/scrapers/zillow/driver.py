"""
This file provides the get_accounts_info() function for Zillow (https://www.zillow.com)

Example Usage:
```
tables = get_accounts_info(suffix="{url_suffix_for_property}")
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
HOMEPAGE = "https://www.zillow.com/homedetails/"

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


def logon(driver: Chrome, homepage: str, suffix: str) -> None:
    """
    Opens and signs on to an account
    :param driver: The browser application
    :param homepage: The logon url to initially navigate
    :param suffix: The URL suffix after 'https://www.zillow.com/homedetails/' to use to identify the property
    """
    # Property Page
    driver.get(homepage + suffix)


def seek_accounts_data(driver: Chrome, wait: WebDriverWait) -> WebElement:
    """
    Navigate the website and find the accounts data for the user
    :param driver: The Chrome browser application
    :param wait: WebDriverWait object for the driver
    :return: The web element of the accounts data
    """
    zestimate: WebElement = wait_and_find_element(
        driver,
        wait,
        (
            By.XPATH,
            "//p/button[contains(text(),'Zestimate')]/../../h3[contains(text(),'$')]",
        ),
    )

    return zestimate


def parse_accounts_summary(zestimate: WebElement) -> pd.DataFrame:
    """
    Post-processing of the table html
    :param zestimate: The web element containing the zestimate for this property
    :return: A pandas dataframe of the data
    """
    # Create a simple dataframe from the input amount
    df = pd.DataFrame(data={"zestimate": [zestimate.text]})

    # Return the dataframe
    return df


def get_accounts_info(suffix: str) -> List[pd.DataFrame]:
    """
    Gets the accounts info for a given user/pass as a list of pandas dataframes
    :param suffix: The URL suffix after 'https://www.zillow.com/homedetails/' to use to identify the property
    :return: A list of pandas dataframes of accounts info tables
    """
    # Get Driver config
    chrome_options: ChromeOptions = get_chrome_options(CHROME_OPTIONS)

    # Instantiating the Driver
    driver: Chrome = start_chromedriver(chrome_options)
    wait: WebDriverWait = WebDriverWait(driver, TIMEOUT)

    # Navigate to the logon page and submit credentials
    logon(driver, HOMEPAGE, suffix)

    # Navigate the site and download the accounts data
    accounts_data: WebElement = seek_accounts_data(driver, wait)
    accounts_data_df: pd.DataFrame = parse_accounts_summary(accounts_data)

    # Process tables
    return_tables: List[pd.DataFrame] = [accounts_data_df]

    # Clean up
    driver.quit()

    # Return list of pandas df
    return return_tables
