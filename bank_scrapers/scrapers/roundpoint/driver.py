"""
This file provides the get_accounts_info() function for RoundPoint Mortgage (https://www.roundpointmortgage.com/)

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
HOMEPAGE: str = "https://loansphereservicingdigital.bkiconnect.com/servicinghome/#/login"

# Timeout
TIMEOUT: int = 30

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
    Note that this function only covers Email Me options for now.
    :param driver: The Chrome driver/browser used for this function
    :param wait: The wait object associated with the driver function above
    """
    # Select the mobile app 2FA option
    mat_radio_group: WebElement = wait_and_find_element(
        driver, wait, (By.CLASS_NAME, "mat-radio-group")
    )

    # Identify MFA options
    options: List[WebElement] = mat_radio_group.find_elements(
        By.CLASS_NAME, "ng-star-inserted"
    )

    # Prompt user input for MFA option
    for i, o in enumerate(options):
        print(f"{i}: {o.text}")
    o_index: int = int(input("Please select one: "))

    # Click based on user input
    mfa_option: WebElement = wait.until(EC.element_to_be_clickable(options[o_index]))
    mfa_option.click()

    submit: WebElement = wait_and_find_click_element(
        driver, wait, (By.XPATH, "//bki-one-time-pin-verify//button[@type='submit']")
    )
    submit.click()

    otp: WebElement = wait_and_find_element(
        driver, wait, (By.XPATH, "//bki-one-time-pin-verify//input[@name='otpInput']")
    )
    code: str = input("OTP: ")
    otp.send_keys(code)

    submit: WebElement = wait_and_find_element(
        driver, wait, (By.XPATH, "//bki-one-time-pin-verify//button[@type='submit']")
    )
    driver.execute_script("arguments[0].click();", submit)


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

    # TOS
    tos: WebElement = wait_and_find_click_element(
        driver, wait, (By.ID, "agreeToTerms-input")
    )
    driver.execute_script("arguments[0].click();", tos)

    # Submit credentials
    submit: WebElement = wait_and_find_click_element(
        driver, wait, (By.XPATH, "//button[@type='submit'][1]")
    )
    driver.execute_script("arguments[0].click();", submit)

    # Jump over confirmation page and go to dashboard
    sleep(1)
    driver.get(
        "https://loansphereservicingdigital.bkiconnect.com/servicinghome/#/dashboard"
    )


def seek_accounts_data(driver: Chrome, wait: WebDriverWait) -> str:
    """
    Navigate the website and click download button for the accounts data
    :param driver: The Chrome browser application
    :param wait: WebDriverWait object for the driver
    """
    amount: str = wait_and_find_element(driver, wait, (By.CLASS_NAME, "amount")).text
    return amount


def seek_other_data(
    driver: Chrome, wait: WebDriverWait
) -> Tuple[List[WebElement], List[WebElement]]:
    """
    Navigate the website and click download button for the accounts data
    :param driver: The Chrome browser application
    :param wait: WebDriverWait object for the driver
    """
    keys: List[WebElement] = wait_and_find_elements(
        driver, wait, (By.XPATH, "//bki-dashboard-payment//div[@class='col']")
    )
    values: List[WebElement] = wait_and_find_elements(
        driver, wait, (By.XPATH, "//bki-dashboard-payment//div[@class='col strong']")
    )
    return keys, values


def parse_other_data(keys: List[WebElement], values: List[WebElement]) -> pd.DataFrame:
    """
    Parses other loan data, such as monthly payment info, from the Roundpoint site
    :param keys: A list of column headers as web elements. Acts as the left table in a left join
    :param values: A list of column values as web elements
    :return: A pandas dataframe of the data in the table
    """
    # Set up a dict for the df to read
    tbl: Dict = {}
    for i in range(len(keys)):
        tbl[keys[i].text.replace(":", "")] = [values[i].text]

    # Create the df
    df: pd.DataFrame = pd.DataFrame(data=tbl)

    # Int-ify the monthly payment amount column
    df["Monthly Payment Amount"] = df["Monthly Payment Amount"].replace(
        to_replace=r"[^0-9\.\/]+", value="", regex=True
    )

    # Drop columns where all values are null
    df.dropna(axis=1, how="all", inplace=True)

    # Return the df
    return df


def parse_accounts_summary(amount: str) -> pd.DataFrame:
    """
    Post-processing of the downloaded file removing disclaimers and other irrelevant mumbo jumbo
    :param amount: The total amount value of the account taken from the Roundpoint website
    :return: A pandas dataframe of the downloaded data
    """
    # Create a simple dataframe from the input amount
    df = pd.DataFrame(data={"Balance": [str(amount)]})

    # Int-ify the monthly payment amount column
    df = df.replace(to_replace=r"[^0-9\.]+", value="", regex=True)

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

    # If 2FA...
    def is_2fa_redirect():
        if str("Verify your account") in driver.page_source:
            return True

    # Wait for redirect to landing page or 2FA
    try:
        wait.until(
            lambda driver: "https://loansphereservicingdigital.bkiconnect.com/servicinghome/#/dashboard"
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
        lambda driver: "https://loansphereservicingdigital.bkiconnect.com/servicinghome/#/dashboard"
        in driver.current_url
    )

    # Navigate the site and download the accounts data
    amount = seek_accounts_data(driver, wait)
    amount_df = parse_accounts_summary(amount)

    other_data_keys, other_data_values = seek_other_data(driver, wait)
    other_data_df = parse_other_data(other_data_keys, other_data_values)

    # Process tables
    return_tables: List[pd.DataFrame] = [amount_df, other_data_df]

    # Clean up
    driver.quit()

    # Return list of pandas df
    return return_tables
