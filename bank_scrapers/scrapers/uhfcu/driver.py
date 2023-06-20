"""
This file provides the get_accounts_info() function for UHFCU (https://online.uhfcu.com)

Example Usage:
```
tables = get_accounts_info(username="{username}", password="{password}")
for t in tables:
    print(t.to_string())
```
"""

# Standard Library Imports
from time import sleep
from typing import Dict

# Non-Standard Imports
import pandas as pd
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By

# Local Imports
from bank_scrapers.scrapers.common.functions import *

# Logon page
HOMEPAGE: str = "https://online.uhfcu.com/sign-in?user=&SubmitNext=Sign%20On"

# Timeout
TIMEOUT: int = 5

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


def handle_multi_factor_authentication(driver: Chrome, wait: WebDriverWait) -> None:
    """
    Navigates the MFA workflow for this website
    :param driver: The Chrome driver/browser used for this function
    :param wait: The wait object associated with the driver function above
    """
    # Find the 2FA options presented by the app
    options_buttons: List[WebElement] = wait_and_find_elements(
        driver, wait, (By.XPATH, "//h2[contains(text(), 'Security Checks')]/../button")
    )

    # Prompt user input for MFA option
    for i, l in enumerate(options_buttons):
        print(f"{i}: {l.text}")
    l_index: int = int(input("Please select one: "))

    # Click based on user input
    mfa_option: WebElement = wait.until(
        EC.element_to_be_clickable(options_buttons[l_index])
    )
    mfa_option.click()

    # Click submit once it becomes clickable
    submit: WebElement = wait_and_find_click_element(
        driver, wait, (By.XPATH, "//button[contains(text(), 'Get Code')]")
    )
    submit.click()

    # Prompt user for OTP code and enter onto the page
    otp_input: WebElement = wait_and_find_element(
        driver, wait, (By.XPATH, "//h2[contains(text(), 'Security Checks')]/..//input")
    )
    otp_code: str = input("Enter 2FA Code: ")
    otp_input.send_keys(otp_code)

    # Click submit once it becomes clickable
    submit: WebElement = wait_and_find_click_element(
        driver,
        wait,
        (By.XPATH, "//mat-dialog-container//button[contains(text(), 'Sign In')]"),
    )
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
    user: WebElement = wait_and_find_click_element(driver, wait, (By.ID, "username"))
    user.send_keys(username)

    # Enter Password
    passwd: WebElement = wait_and_find_element(driver, wait, (By.ID, "password"))
    passwd.send_keys(password)
    sleep(2)

    # Submit will sometimes stay inactive unless interacted with
    submit: WebElement = wait_and_find_click_element(
        driver, wait, (By.XPATH, "//button[@type='submit']")
    )
    submit.click()


def seek_credit_accounts_data(
    driver: Chrome, wait: WebDriverWait, t: WebElement
) -> None:
    """
    Navigate the website to get to the credit accounts details subpage
    :param driver: The Chrome browser application
    :param wait: WebDriverWait object for the driver
    :param t: The table on the dashboard which is being navigated for info
    """
    # Click into the credit card table
    t.click()

    # Navigate to the Manage Cards button on the page and click it
    manage_cards_btn: WebElement = wait_and_find_click_element(
        driver, wait, (By.XPATH, "//app-manage-cards//button")
    )
    manage_cards_btn.click()
    sleep(3)

    # Switch to the new window
    driver.switch_to.window(driver.window_handles[1])


def parse_credit_card_info(driver: Chrome, wait: WebDriverWait) -> pd.DataFrame:
    """
    Parses the info on the credit card accounts screen into a pandas df
    :param driver: The Chrome browser application
    :param wait: WebDriverWait object for the driver
    :return: A pandas dataframe of the credit card accounts data on the page
    """
    # Identify the account info rows on the screen
    data_tbl: WebElement = wait_and_find_element(
        driver, wait, (By.XPATH, "//div[@class='module module-condensed'][1]")
    )

    # Pull each row as a newline separated kv pair
    data: List[WebElement] = wait_and_find_elements(
        data_tbl, wait, (By.XPATH, "//*[@class='text-underlined grid']")
    )
    data_txt: List[str] = list(i.text for i in data)

    # Split the kv pairs and enter into a dict
    data_dict: Dict = {}
    for d in data_txt:
        data_row = d.split("\n")
        data_dict[data_row[0]] = [data_row[-1]]

    # Make a df from the dict
    df: pd.DataFrame = pd.DataFrame(data=data_dict)

    return df


def parse_accounts_summary(table: WebElement) -> pd.DataFrame:
    """
    Takes a table as a web element from the UHFCU accounts overview page and turns it into a pandas df
    :param table: The table as a web element
    :return: A pandas dataframe of the table
    """
    # Get a list of the card text
    account_info: List[str] = table.text.split(sep="\n")

    # Remove the first element (Share Account title)
    account_info.pop(0)

    # Data
    account_type: str = account_info.pop(0)
    account_desc: str = account_info.pop(0)

    # The remaining elements are alternating kv pairs as list elements, so split and zip
    balance_infos: zip = zip(
        list(e for i, e in enumerate(account_info) if i % 2 == 0),
        list(e for i, e in enumerate(account_info) if i % 2 != 0),
    )

    # Data
    balance_dict: Dict = {"Account Type": account_type, "Account Desc": account_desc}
    for info in balance_infos:
        # Append balance_dict with the tuple values zipped above
        balance_dict[info[0]] = [info[1]]

    # Make a df from the dict
    df: pd.DataFrame = pd.DataFrame(data=balance_dict)

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
        if "Security Checks" in driver.page_source:
            return True

    # Wait for redirect to landing page or 2FA
    try:
        wait.until(
            lambda driver: "https://online.uhfcu.com/consumer/main/dashboard"
            in driver.current_url
            or is_2fa_redirect()
        )
    except TimeoutException as e:
        leave_on_timeout(driver)

    # Handle 2FA if prompted, or quit if Chase catches us
    if is_2fa_redirect():
        handle_multi_factor_authentication(driver, wait)

    # Wait for landing page after handling 2FA
    wait.until(
        lambda driver: "https://online.uhfcu.com/consumer/main/dashboard"
        in driver.current_url
    )

    # Process tables
    tables: List[WebElement] = wait_and_find_elements(
        driver, wait, (By.XPATH, "//app-sub-accounts-tiles//app-sub-account-card")
    )
    return_tables: List = []
    for t in tables:
        if "Share Account" in t.text:
            return_tables.append(parse_accounts_summary(t))
        if "Loan Account" in t.text:
            seek_credit_accounts_data(driver, wait, t)
            return_tables.append(parse_credit_card_info(driver, wait))

    # Clean up
    driver.quit()

    # Return list of pandas df
    return return_tables
