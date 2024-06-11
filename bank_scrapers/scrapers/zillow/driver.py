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
from typing import List, Tuple
from datetime import datetime

# Non-Standard Imports
import pandas as pd
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from undetected_chromedriver import Chrome, ChromeOptions
from pyvirtualdisplay import Display

# Local Imports
from bank_scrapers.scrapers.common.functions import (
    start_chromedriver,
    get_chrome_options,
    wait_and_find_element,
    screenshot_on_timeout,
)
from bank_scrapers.common.functions import convert_to_prometheus, search_for_dir

# Institution info
INSTITUTION: str = "Zillow"
SYMBOL: str = "USD"

# Logon page
HOMEPAGE = "https://www.zillow.com/homedetails/"

# Timeout
TIMEOUT: int = 15

# Chrome config
CHROME_OPTIONS: List[str] = [
    "--no-sandbox",
    "--window-size=1920,1080",
    "--disable-gpu",
    "--allow-running-insecure-content",
]

# Error screenshot config
ERROR_DIR: str = f"{search_for_dir(__file__, "errors")}/errors"


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
def logon(driver: Chrome, homepage: str, suffix: str) -> None:
    """
    Opens and signs on to an account
    :param driver: The browser application
    :param homepage: The logon url to initially navigate
    :param suffix: The URL suffix after 'https://www.zillow.com/homedetails/' to use to identify the property
    """
    # Property Page
    driver.get(homepage + suffix)


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
def seek_accounts_data(
    driver: Chrome, wait: WebDriverWait
) -> Tuple[WebElement, WebElement]:
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

    address: WebElement = wait_and_find_element(
        driver, wait, (By.XPATH, "//div[@class='summary-container']//h1")
    )

    return address, zestimate


def parse_accounts_summary(address: WebElement, zestimate: WebElement) -> pd.DataFrame:
    """
    Post-processing of the table data
    :param address: The web element containing the address for this property
    :param zestimate: The web element containing the zestimate for this property
    :return: A pandas dataframe of the data
    """
    # Create a simple dataframe from the input amount
    df: pd.DataFrame = pd.DataFrame(
        data={
            "address": [address.text],
            "zestimate": [zestimate.text],
            "symbol": [SYMBOL],
            "account_type": ["real_estate"],
        }
    )

    # Remove non-digits from the value
    df["zestimate"]: pd.DataFrame = df["zestimate"].replace(
        to_replace=r"[^0-9]+", value="", regex=True
    )

    # Return the dataframe
    return df


def get_accounts_info(
    suffix: str, prometheus: bool = False
) -> List[pd.DataFrame] | List[Tuple[List, float]]:
    """
    Gets the accounts info for a given user/pass as a list of pandas dataframes
    :param suffix: The URL suffix after 'https://www.zillow.com/homedetails/' to use to identify the property
    :param prometheus: True/False value for exporting as Prometheus-friendly exposition
    :return: A list of pandas dataframes of accounts info tables
    """
    # Instantiate the virtual display
    display: Display = Display(visible=False, size=(800, 600))
    display.start()

    # Get Driver config
    chrome_options: ChromeOptions = get_chrome_options(CHROME_OPTIONS)

    # Instantiating the Driver
    driver: Chrome = start_chromedriver(chrome_options)
    wait: WebDriverWait = WebDriverWait(driver, TIMEOUT)

    # Navigate to the logon page and submit credentials
    logon(driver, HOMEPAGE, suffix)

    # Navigate the site and download the accounts data
    address: WebElement
    zestimate: WebElement
    address, zestimate = seek_accounts_data(driver, wait)
    accounts_data_df: pd.DataFrame = parse_accounts_summary(address, zestimate)

    # Process tables
    return_tables: List[pd.DataFrame] = [accounts_data_df]

    # Clean up
    driver.quit()

    # Convert to Prometheus exposition if flag is set
    if prometheus:
        return_tables: List[Tuple[List, float]] = convert_to_prometheus(
            return_tables,
            INSTITUTION,
            "address",
            "symbol",
            "zestimate",
            "account_type",
        )

    # Return list of pandas df
    return return_tables
