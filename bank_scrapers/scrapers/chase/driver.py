"""
This file provides the get_accounts_info() function for Chase (https://www.chase.com)

Example Usage:
```
tables = get_accounts_info(username="{username}", password="{password}")
for t in tables:
    print(t.to_string())
```
"""

# Standard Library Imports
from typing import Dict
from time import sleep

# Non-Standard Imports
import pandas as pd
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By

# Local Imports
from bank_scrapers.scrapers.common.functions import *

# Logon page
HOMEPAGE: str = "https://www.chase.com/personal/credit-cards/login-account-access"

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


def handle_multi_factor_authentication(
    driver: Chrome, wait: WebDriverWait, password: str
) -> None:
    """
    Navigates the MFA workflow for this website
    Note that this function only covers Email Me options for now.
    :param driver: The Chrome driver/browser used for this function
    :param wait: The wait object associated with the driver function above
    :param password: User's password to enter along with OPT
    """
    # Wait for the expand option to become clickable or else can lead to bugs where the list doesn't expand correctly
    expand_button: WebElement = wait_and_find_click_element(
        driver, wait, (By.ID, "header-simplerAuth-dropdownoptions-styledselect")
    )

    # Then click it
    expand_button.click()
    sleep(0.5)

    # Identify MFA options
    labels: List[WebElement] = wait_and_find_elements(
        driver, wait, (By.XPATH, "//a[@role='option']")
    )

    # Prompt user input for MFA option
    for i, l in enumerate(labels):
        print(f"{i}: {l.text}")
    l_index: int = int(input("Please select one: "))

    # Click based on user input
    expand_button.click()
    mfa_option: WebElement = wait.until(EC.element_to_be_clickable(labels[l_index]))
    mfa_option.click()

    # Click submit once it becomes clickable
    submit: WebElement = wait_and_find_click_element(
        driver, wait, (By.ID, "requestIdentificationCode-sm")
    )
    submit.click()

    # Prompt user for OTP code and enter onto the page
    otp_input: WebElement = wait_and_find_element(
        driver, wait, (By.ID, "otpcode_input-input-field")
    )
    otp_code: str = input("Enter 2FA Code: ")
    otp_input.send_keys(otp_code)

    # Re-enter the password on the OTP page
    pwd_input: WebElement = wait_and_find_element(
        driver, wait, (By.ID, "password_input-input-field")
    )
    pwd_input.send_keys(password)

    # Click submit once it becomes clickable
    submit: WebElement = wait_and_find_element(
        driver, wait, (By.ID, "log_on_to_landing_page-sm")
    )
    wait.until(EC.element_to_be_clickable((By.ID, "log_on_to_landing_page-sm")))
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

    # Navigate iframe
    iframe: WebElement = wait_and_find_element(
        driver, wait, (By.ID, "routablecpologonbox")
    )
    driver.switch_to.frame(iframe)

    # Enter User
    user: WebElement = wait_and_find_click_element(
        driver, wait, (By.ID, "userId-text-input-field")
    )
    user.click()
    user.send_keys(username)

    # Enter Password
    passwd: WebElement = wait_and_find_element(
        driver, wait, (By.ID, "password-text-input-field")
    )
    passwd.send_keys(password)

    # Submit will sometimes stay inactive unless interacted with
    submit: WebElement = wait_and_find_element(driver, wait, (By.ID, "signin-button"))
    submit.send_keys("")
    wait.until(EC.element_to_be_clickable((By.ID, "signin-button")))
    submit.click()


def seek_accounts_data(driver: Chrome, wait: WebDriverWait) -> None:
    """
    Navigate the website and click download button for the accounts data
    :param driver: The Chrome browser application
    :param wait: WebDriverWait object for the driver
    """
    # Navigate shadow root
    shadow_root: ShadowRoot = wait_and_find_element(
        driver, wait, (By.ID, "multiMoreMenuParent-3")
    ).shadow_root
    sr_wait: WebDriverWait = WebDriverWait(shadow_root, 60)

    # Open accounts dropdown
    accounts_dropdown: WebElement = wait_and_find_element(
        shadow_root, sr_wait, (By.CLASS_NAME, "button--tertiary")
    )
    accounts_dropdown.click()

    # Navigate another shadow root
    sr: ShadowRoot = wait_and_find_element(
        shadow_root, sr_wait, (By.CLASS_NAME, "mds-menu-button--cpo")
    ).shadow_root

    # Wait for the account details button to be clickable and go to it
    sr_wait_: WebDriverWait = WebDriverWait(sr, 60)
    btn: WebElement = wait_and_find_click_element(
        sr, sr_wait_, (By.CLASS_NAME, "menu-button-item")
    )
    btn.click()


def parse_accounts_summary(table: WebElement) -> pd.DataFrame:
    """
    Takes a table as a web element from the Chase accounts overview page and turns it into a pandas df
    :param table: The table as a web element
    :return: A pandas dataframe of the table
    """

    #  Transpose vertical headers labels
    dt: List[WebElement] = table.find_elements(By.CLASS_NAME, "DATALABELH")
    dt_txt: List[str] = list(d.text for d in dt)

    # Data
    dd: List[WebElement] = table.find_elements(By.CLASS_NAME, "DATA")
    dd_txt: List[str] = list(d.text for d in dd)

    # "zip" the data as a dict
    tbl: Dict = {}
    for i in range(len(dt)):
        tbl[dt_txt[i]] = [dd_txt[i]]

    # Make a df from the dict
    df: pd.DataFrame = pd.DataFrame(data=tbl)

    # Take out non-numbers/decimals
    df: pd.DataFrame = df.replace(to_replace=r"[^0-9\.]+", value="", regex=True)

    # Drop any all-null columns
    df: pd.DataFrame = df.dropna(axis=1, how="all")

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

    # If 2FA...
    def is_2fa_redirect():
        if (
            "chase.com/web/auth/" in driver.current_url
            and "We don't recognize this device" in driver.page_source
        ):
            return True

    def password_needs_reset():
        if (
            "chase.com/web/auth/" in driver.current_url
            and "We can't find that username and password" in driver.page_source
            and "Keep in mind: You won't be able to see your statements and notices until you reset your password."
            in driver.page_source
        ):
            return True

    # Wait for redirect to landing page or 2FA
    try:
        wait.until(
            lambda driver: "chase.com/web/auth/dashboard#/dashboard/overviewAccounts/overview/singleCard"
            in driver.current_url
            or is_2fa_redirect()
            or password_needs_reset()
        )
    except TimeoutException as e:
        leave_on_timeout(driver)

    # Handle 2FA if prompted, or quit if Chase catches us
    if is_2fa_redirect():
        handle_multi_factor_authentication(driver, wait, password)
    elif password_needs_reset():
        print("Password needs reset!")
        sys.exit(1)

    # Wait for landing page after handling 2FA
    wait.until(
        lambda driver: "chase.com/web/auth/dashboard#/dashboard/overviewAccounts/overview/singleCard"
        in driver.current_url
    )

    # Navigate the site and download the accounts data
    seek_accounts_data(driver, wait)

    # Process tables
    tables: List[WebElement] = wait_and_find_elements(
        driver, wait, (By.CLASS_NAME, "details-bar")
    )
    return_tables: List = []
    for t in tables:
        return_tables.append(parse_accounts_summary(t))

    # Clean up
    driver.quit()

    # Return list of pandas df
    return return_tables
