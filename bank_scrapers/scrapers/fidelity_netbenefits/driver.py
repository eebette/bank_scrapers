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
from time import sleep

# Non-Standard Imports
import pandas as pd
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By

# Local Imports
from bank_scrapers.scrapers.common.functions import *

# Logon page
HOMEPAGE: str = (
    "https://login.fidelity.com/ftgw/Fas/Fidelity/NBPart/Login/Init?ISPBypass=true"
)

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


def enable_downloads(driver: Chrome, downloads_dir: str) -> None:
    """
    Creates a tmp directory and sets chrome experimental options to enable downloads there
    :param driver: The Chrome object for which to enable downloads
    :param downloads_dir: The directory to use to handle downloaded files
    :return: The same chrome options with downloads enabled to tmp dir
    """
    params = {"behavior": "allow", "downloadPath": downloads_dir}
    driver.execute_cdp_cmd("Page.setDownloadBehavior", params)


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


def handle_multi_factor_authentication(driver: Chrome, wait: WebDriverWait) -> None:
    """
    Navigates the MFA workflow for this website
    Note that this function only covers Email Me options for now.
    :param driver: The Chrome driver/browser used for this function
    :param wait: The wait object associated with the driver function above
    """
    # Navigate the page's shadow roots and select the email 2FA option
    shadow_root: ShadowRoot = wait_and_find_element(
        driver, wait, (By.XPATH, "//pvd-expand-collapse[@title='Email Me'][1]")
    ).shadow_root
    shadow_wait: WebDriverWait = WebDriverWait(shadow_root, 5)

    # Wait for the expand option to become clickable or else can lead to bugs where the list doesn't expand correctly
    shadow_wait.until(
        EC.element_to_be_clickable((By.CLASS_NAME, "expand-collapse-trigger"))
    )
    expand_button: WebElement = shadow_root.find_element(
        By.CLASS_NAME, "expand-collapse-trigger"
    )

    # Then click it
    expand_button.click()

    # Identify MFA options
    labels: List[WebElement] = wait_and_find_elements(
        driver, wait, (By.XPATH, '//*[@id="email-me-expand-collapse"]/div/div/label')
    )

    # Prompt user input for MFA option
    for i, l in enumerate(labels):
        print(f"{i}: {l.text}")
    l_index: int = int(input("Please select one: "))

    # Click based on user input
    # wait.until(EC.element_to_be_clickable(labels[l_index]))
    labels[l_index].click()

    # Click submit once it becomes clickable
    submit: WebElement = wait_and_find_element(driver, wait, (By.ID, "submit"))
    wait.until(EC.element_to_be_clickable((By.ID, "submit")))
    submit.click()

    # Prompt user for OTP code and enter onto the page
    otp_input: WebElement = wait_and_find_element(
        driver, wait, (By.ID, "security-code")
    )
    otp_code: str = input("Enter 2FA Code: ")
    otp_input.send_keys(otp_code)

    # Click submit once it becomes clickable
    submit: WebElement = wait_and_find_element(driver, wait, (By.ID, "submit"))
    wait.until(EC.element_to_be_clickable((By.ID, "submit")))
    submit.click()


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
    user: WebElement = wait_and_find_element(driver, wait, (By.ID, "userId"))
    user.send_keys(username)

    # Enter Password
    passwd: WebElement = wait_and_find_element(driver, wait, (By.ID, "password"))
    passwd.send_keys(password)

    # Submit
    submit: WebElement = wait_and_find_element(
        driver, wait, (By.CSS_SELECTOR, ".buttons > button:nth-child(1)")
    )
    submit.click()


def seek_accounts_data(driver: Chrome, wait: WebDriverWait) -> None:
    """
    Navigate the website and click download button for the accounts data
    :param driver: The Chrome browser application
    :param wait: WebDriverWait object for the driver
    """
    # Go to the accounts page
    driver.get("https://digital.fidelity.com/ftgw/digital/portfolio/positions")

    # Wait for the downloads button to be clickable
    download_btn: WebElement = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[@aria-label='Download Positions']")
        )
    )

    # Click the button
    download_btn.click()

    # Sleep time to make sure the download completes
    sleep(3)


def parse_accounts_summary(full_path: str) -> pd.DataFrame:
    """
    Post-processing of the downloaded file removing disclaimers and other irrelevant mumbo jumbo
    :param full_path: The path to the file to parse
    :return: A pandas dataframe of the downloaded data
    """
    df: pd.DataFrame = pd.read_csv(f"{full_path}", on_bad_lines="skip")
    df: pd.DataFrame = df[df["Quantity"].notna()]
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
    options: Options = get_chrome_options(CHROME_OPTIONS)

    # Instantiating the Driver
    driver: Chrome = start_chromedriver(options)
    wait: WebDriverWait = WebDriverWait(driver, TIMEOUT)

    enable_downloads(driver, downloads_dir=tmp_dir)
    # Navigate to the logon page and submit credentials
    logon(driver, wait, HOMEPAGE, username, password)

    # Wait for redirect to landing page or 2FA
    try:
        wait.until(
            lambda driver: "https://workplaceservices.fidelity.com/"
            in driver.current_url
            or str("Extra security step required") in driver.page_source
        )
    except TimeoutException as e:
        leave_on_timeout(driver)

    # If 2FA...
    def is_2fa_redirect():
        if (
            "https://login.fidelity.com/" in driver.current_url
            and str("Extra security step required") in driver.page_source
        ):
            return True

    if is_2fa_redirect():
        handle_multi_factor_authentication(driver, wait)

    # Wait for redirect to landing page
    wait.until(
        lambda driver: "https://workplaceservices.fidelity.com/" in driver.current_url
    )

    # Navigate the site and download the accounts data
    seek_accounts_data(driver, wait)

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
