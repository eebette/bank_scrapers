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

# Non-Standard Imports
from time import sleep

import pandas as pd
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By

# Local Imports
from bank_scrapers.scrapers.common.functions import *

# Logon page
HOMEPAGE = "https://logon.vanguard.com/logon"

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


def enable_downloads(driver: Chrome, downloads_dir: str) -> None:
    """
    Enable downloads for an instance of undetectable Chrome
    :param driver: The Chrome object for which to enable downloads
    :param downloads_dir: The directory to use to handle downloaded files
    :return: The same chrome options with downloads enabled to tmp dir
    """
    # Defines autodownload and download PATH
    params = {"behavior": "allow", "downloadPath": downloads_dir}
    driver.execute_cdp_cmd("Page.setDownloadBehavior", params)


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


def handle_multi_factor_authentication(driver: Chrome, wait: WebDriverWait) -> None:
    """
    Navigates the MFA workflow for this website
    Note that this function only covers Email Me options for now.
    :param driver: The Chrome driver/browser used for this function
    :param wait: The wait object associated with the driver function above
    """
    # Select the mobile app 2FA option
    app_verification_btn = wait_and_find_click_element(
        driver, wait, (By.CSS_SELECTOR, "button.col-md:nth-child(1) > div:nth-child(1)")
    )
    app_verification_btn.click()

    # Prompt user for 2FA
    print("Waiting for 2FA...")


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
    user: WebElement = wait_and_find_click_element(driver, wait, (By.ID, "USER"))
    user.send_keys(username)

    # Enter Password
    passwd: WebElement = wait_and_find_element(
        driver, wait, (By.ID, "PASSWORD-blocked")
    )
    passwd.send_keys(password)

    # Submit credentials
    submit: WebElement = wait_and_find_click_element(
        driver, wait, (By.ID, "username-password-submit-btn")
    )
    submit.click()


def seek_accounts_data(driver: Chrome, wait: WebDriverWait, tmp_dir: str) -> None:
    """
    Navigate the website and click download button for the accounts data
    :param driver: The Chrome browser application
    :param wait: WebDriverWait object for the driver
    :param tmp_dir: An empty directory to use for processing the downloaded file
    """
    # Go to Downloads Center
    driver.get(
        "https://personal1.vanguard.com/ofu-open-fin-exchange-webapp/ofx-welcome"
    )

    # Select CSV option for download formats
    download_option: WebElement = wait_and_find_click_element(
        driver, wait, (By.ID, "optionSelect")
    )
    download_option.click()

    vui_option: WebElement = wait_and_find_click_element(
        driver, wait, (By.ID, "vuioption2")
    )
    vui_option.click()

    # Select last 18 months for date range
    date_range: WebElement = wait_and_find_click_element(
        driver, wait, (By.ID, "dateSelect")
    )
    date_range.click()

    vui_option: WebElement = wait_and_find_click_element(
        driver, wait, (By.ID, "vui-option-7")
    )
    vui_option.click()

    # Select for all accounts
    wait.until(EC.presence_of_element_located((By.ID, "mat-checkbox-1-input")))
    mat_checkbox = wait_and_find_click_element(
        driver, wait, (By.ID, "mat-checkbox-1-input")
    )
    mat_checkbox.click()

    # Submit download request
    submit: WebElement = wait_and_find_click_element(driver, wait, (By.ID, "submitOFXDownload"))
    submit.click()

    # Allow the download to process
    while not os.path.exists(f"{tmp_dir}/OfxDownload.csv"):
        sleep(1)


def parse_accounts_summary(full_path: str) -> pd.DataFrame:
    """
    Post-processing of the downloaded file removing disclaimers and other irrelevant mumbo jumbo
    :param full_path: The path to the file to parse
    :return: A pandas dataframe of the downloaded data
    """
    df: pd.DataFrame = pd.read_csv(f"{full_path}", on_bad_lines="skip")
    df: pd.DataFrame = df.dropna(axis=1, how="all")
    return df


def get_accounts_info(username: str, password: str, tmp_dir: str) -> List[pd.DataFrame]:
    """
    Gets the accounts info for a given user/pass as a list of pandas dataframes
    :param username: Your username for logging in
    :param password: Your password for logging in
    :param tmp_dir: An empty directory to use for processing the downloaded file
    :return: A list of pandas dataframes of accounts info tables
    """
    # Get Driver config
    chrome_options: ChromeOptions = get_chrome_options(CHROME_OPTIONS)

    # Instantiating the Driver
    driver: Chrome = start_chromedriver(chrome_options)
    enable_downloads(driver, downloads_dir=tmp_dir)
    wait: WebDriverWait = WebDriverWait(driver, TIMEOUT)

    # Navigate to the logon page and submit credentials
    logon(driver, wait, HOMEPAGE, username, password)

    # If 2FA...
    def is_2fa_redirect():
        if (
            driver.current_url == "https://logon.vanguard.com/logon"
            and str("We need to verify it's you") in driver.page_source
        ):
            return True

    # Wait for redirect to landing page or 2FA
    try:
        wait.until(
            lambda driver: "https://dashboard.web.vanguard.com/" in driver.current_url
            or "https://challenges.web.vanguard.com/" in driver.current_url
            or is_2fa_redirect()
        )
    except TimeoutException as e:
        leave_on_timeout(driver)

    # Handle 2FA if prompted, or quit if Chase catches us
    if is_2fa_redirect():
        handle_multi_factor_authentication(driver, wait)

    # Wait for landing page after handling 2FA
    wait.until(
        lambda driver: "https://dashboard.web.vanguard.com/" in driver.current_url
        or "https://challenges.web.vanguard.com/" in driver.current_url
    )

    # Navigate the site and download the accounts data
    seek_accounts_data(driver, wait, tmp_dir)

    # Process tables
    file_name: str = os.listdir(tmp_dir)[0]
    return_tables: List[pd.DataFrame] = [
        parse_accounts_summary(f"{tmp_dir}/{file_name}")
    ]

    # Clean up
    driver.quit()
    os.remove(f"{tmp_dir}/{file_name}")

    # Return list of pandas df
    return return_tables
