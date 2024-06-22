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
from typing import List, Tuple, Dict, Union
from datetime import datetime

# Non-Standard Imports
import pandas as pd
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from undetected_chromedriver import Chrome, ChromeOptions

# Local Imports
from bank_scrapers import ROOT_DIR
from bank_scrapers.common.functions import convert_to_prometheus, search_files_for_int
from bank_scrapers.common.log import log
from bank_scrapers.common.types import PrometheusMetric
from bank_scrapers.scrapers.common.functions import (
    start_chromedriver,
    get_chrome_options,
    wait_and_find_element,
    wait_and_find_elements,
    wait_and_find_click_element,
    screenshot_on_timeout,
)
from bank_scrapers.scrapers.common.mfa_auth import MfaAuth

# Institution info
INSTITUTION: str = "RoundPoint Mortgage"
SYMBOL: str = "USD"

# Logon page
HOMEPAGE: str = (
    "https://loansphereservicingdigital.bkiconnect.com/servicinghome/#/login"
)
DASHBOARD_PAGE: str = (
    "https://loansphereservicingdigital.bkiconnect.com/servicinghome/#/dashboard"
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
def handle_multi_factor_authentication(
    driver: Chrome, wait: WebDriverWait, mfa_auth: MfaAuth = None
) -> None:
    """
    Navigates the MFA workflow for this website
    :param driver: The Chrome driver/browser used for this function
    :param wait: The wait object associated with the driver function above
    :param mfa_auth: A typed dict containing an int representation of the MFA contact opt. and a dir containing the OTP
    """
    log.info(f"Redirected to two-factor authentication page.")

    # Identify MFA options
    log.info(f"Finding contact options elements...")
    options: List[WebElement] = wait_and_find_elements(
        driver, wait, (By.XPATH, "//div[@id='otpOption']//input[@type='radio']")
    )

    log.info(f"Finding labels for contact options elements...")
    labels: List[WebElement] = wait_and_find_elements(
        driver, wait, (By.XPATH, "//div[@id='otpOption']//label[@class='mdc-label']")
    )

    # Prompt user input for MFA option
    if mfa_auth is None:
        log.info(f"No automation info provided. Prompting user for contact option.")
        for i, l in enumerate(labels):
            print(f"{i + 1}: {l.text}")
        o_index: int = int(input("Please select one: ")) - 1
    else:
        log.info(f"Contact option found in automation info.")
        o_index: int = mfa_auth["otp_contact_option"] - 1
    log.debug(f"Contact option: {o_index}")

    # Click based on user input
    log.info(f"Clicking element for user selected contact option...")
    mfa_option: WebElement = options[o_index]
    mfa_option.click()

    # Click submit once it becomes clickable
    log.info(f"Finding submit button element and waiting for it to be clickable...")
    submit: WebElement = wait_and_find_click_element(
        driver, wait, (By.XPATH, "//bki-one-time-pin-verify//button[@type='submit']")
    )

    log.info(f"Clicking submit button element...")
    submit.click()

    # Prompt user for OTP code and enter onto the page
    log.info(f"Finding input box element for OTP...")
    otp: WebElement = wait_and_find_element(
        driver, wait, (By.XPATH, "//bki-one-time-pin-verify//input[@name='otpInput']")
    )
    if mfa_auth is None:
        log.info(f"No automation info provided. Prompting user for OTP.")
        otp_code: str = input("Enter OTP Code: ")
    else:
        log.info(
            f"OTP file location found in automation info: {mfa_auth["otp_code_location"]}"
        )
        otp_code: str = str(
            search_files_for_int(
                mfa_auth["otp_code_location"],
                "Servicing Digital",
                ".txt",
                6,
                10,
                TIMEOUT,
                True,
            )
        )

    log.info(f"Sending info to OTP input box element...")
    otp.send_keys(otp_code)

    # Click submit once it becomes clickable
    log.info(f"Finding submit button element and waiting for it to be clickable...")
    submit: WebElement = wait_and_find_click_element(
        driver, wait, (By.XPATH, "//bki-one-time-pin-verify//button[@type='submit']")
    )
    submit.click()

    # log.info(f"Sleeping for 5 seconds...")
    # sleep(5)

    log.info(
        f"Finding close prompt button element and waiting for it to be clickable..."
    )
    close: WebElement = wait_and_find_click_element(
        driver, wait, (By.XPATH, "//bki-one-time-pin-verify//button[@type='submit']")
    )

    log.info(f"Clicking close prompt button element...")
    close.click()


def is_mfa_redirect(driver: Chrome) -> bool:
    """
    Checks and determines if the site is forcing MFA on the login attempt
    :param driver: The browser application
    :return: True if MFA is being enforced
    """
    if str("Verify your account") in driver.page_source:
        return True
    else:
        return False


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
def logon(
    driver: Chrome,
    wait: WebDriverWait,
    homepage: str,
    username: str,
    password: str,
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
    log.info(f"Accessing: {homepage}")
    driver.get(homepage)

    # Enter User
    log.info(f"Finding username element...")
    user: WebElement = wait_and_find_element(driver, wait, (By.ID, "username"))

    log.info(f"Sending info to username element...")
    log.debug(f"Username: {username}")
    user.send_keys(username)

    # Enter Password
    log.info(f"Finding password element...")
    passwd: WebElement = wait_and_find_element(driver, wait, (By.ID, "password"))

    log.info(f"Sending info to password element...")
    passwd.send_keys(password)

    # TOS
    log.info(f"Finding TOS element...")

    # Waiting for clickable doesn't trigger here
    tos: WebElement = wait_and_find_element(
        driver, wait, (By.XPATH, "//input[@id='agreeToTerms-input']")
    )

    log.info(f"Clicking TOS element...")
    tos.click()

    # Submit credentials
    log.info(f"Finding submit button element and waiting for it to be clickable...")
    submit: WebElement = wait_and_find_click_element(
        driver, wait, (By.XPATH, "//button[@type='submit'][1]")
    )

    log.info(f"Clicking submit button element...")
    submit.click()

    # Wait for redirect to landing page or 2FA
    log.info(f"Waiting for redirect...")
    wait.until(
        lambda _: DASHBOARD_PAGE in driver.current_url or is_mfa_redirect(driver)
    )


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
def seek_accounts_data(driver: Chrome, wait: WebDriverWait) -> str:
    """
    Navigate the website and click download button for the accounts data
    :param driver: The Chrome browser application
    :param wait: WebDriverWait object for the driver
    """
    log.info(f"Finding loan amount element...")
    amount: str = wait_and_find_element(driver, wait, (By.CLASS_NAME, "amount")).text
    return amount


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
def seek_other_data(
    driver: Chrome, wait: WebDriverWait
) -> Tuple[List[WebElement], List[WebElement]]:
    """
    Navigate the website and click download button for the accounts data
    :param driver: The Chrome browser application
    :param wait: WebDriverWait object for the driver
    """
    log.info(f"Finding column headers elements...")
    keys: List[WebElement] = wait_and_find_elements(
        driver, wait, (By.XPATH, "//bki-dashboard-payment//div[@class='col']")
    )

    log.info(f"Finding column values elements...")
    values: List[WebElement] = wait_and_find_elements(
        driver, wait, (By.XPATH, "//bki-dashboard-payment//div[@class='col strong']")
    )
    return keys, values


def parse_other_data(keys: List[WebElement], values: List[WebElement]) -> pd.DataFrame:
    """
    Parses other loan data, such as monthly payment info, from the RoundPoint site
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
    df: pd.DataFrame = df.dropna(axis=1, how="all")

    # Return the df
    return df


def parse_accounts_summary(amount: str) -> pd.DataFrame:
    """
    Post-processing of the downloaded file removing disclaimers and other irrelevant mumbo jumbo
    :param amount: The total amount value of the account taken from the RoundPoint website
    :return: A pandas dataframe of the downloaded data
    """
    # Create a simple dataframe from the input amount
    df: pd.DataFrame = pd.DataFrame(data={"Balance": [str(amount)]})

    # Int-ify the monthly payment amount column
    df: pd.DataFrame = df.replace(to_replace=r"[^0-9\.]+", value="", regex=True)

    # Drop columns where all values are null
    df: pd.DataFrame = df.dropna(axis=1, how="all")

    # Return the dataframe
    return df


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
def get_loan_number(driver: Chrome, wait: WebDriverWait) -> str:
    """
    Gets the full loan number from the My Loan page on the RoundPoint website
    :param driver: The Chrome browser application
    :param wait: WebDriverWait object for the driver
    :return: The full loan number as a string
    """
    # Navigate to the My Loan page
    log.info(
        f"Accessing: https://loansphereservicingdigital.bkiconnect.com/servicinghome/#/my-loan"
    )
    driver.get(
        "https://loansphereservicingdigital.bkiconnect.com/servicinghome/#/my-loan"
    )

    # Find the element for the loan number
    log.info(f"Finding loan number element and waiting for it to be clickable...")
    loan_number_element: WebElement = wait_and_find_click_element(
        driver, wait, (By.XPATH, "//bki-myloan-balance//a[@class='card-link']")
    )

    # Click so that the full loan number is exposed
    log.info(f"Clicking loan number element...")
    loan_number_element.click()

    # Get the loan number
    log.info(f"Finding full loan number element...")
    loan_number: str = wait_and_find_element(
        driver, wait, (By.XPATH, "//bki-myloan-balance//span[@isolate='']")
    ).text

    # Return the loan number
    return loan_number


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
def scrape_loan_data(driver: Chrome, wait: WebDriverWait) -> List[pd.DataFrame]:
    """
    Iterates through the account's loans and processes the data into a list of Pandas DataFrames
    :param driver: The Chrome browser application
    :param wait: WebDriverWait object for the driver
    :return: A list of Pandas DataFrames containing the loans data
    """
    # Find and expand the dropdown list containing the account's loans
    log.info(
        f"Finding loans button dropdown element and waiting for it to be clickable..."
    )
    loans_button: WebElement = wait_and_find_click_element(
        driver, wait, (By.XPATH, "//div[@class='secondary-header-top']//button")
    )

    log.info(f"Clicking loans button dropdown element...")
    loans_button.click()

    # Get the list of loans in the dropdown list
    log.info(f"Finding loans button elements...")
    loans_xpath: str = "//div[@id='loanMenuId']//div[contains(@class, 'cursor')]"
    loans: List[WebElement] = wait_and_find_elements(
        driver, wait, (By.XPATH, loans_xpath)
    )

    return_tables: List = list()
    for loan in loans:
        # Go back to dashboard page if not there already
        if driver.current_url != DASHBOARD_PAGE:
            log.info(f"Accessing: {DASHBOARD_PAGE}")
            driver.get(DASHBOARD_PAGE)

        # Must click twice to expand list
        log.info(f"Waiting for loans button dropdown element to be clickable...")
        wait.until(EC.element_to_be_clickable(loans_button))

        log.info(f"Clicking loans button dropdown element...")
        loans_button.click()

        log.info(f"Clicking loans button dropdown element (again)...")
        loans_button.click()

        # Click on the next loan
        log.info(f"Waiting for loan button element to be clickable...")
        wait.until(EC.element_to_be_clickable(loan))

        log.info(f"Clicking loan button element...")
        loan.click()

        # log.info(f"Sleeping for 2 seconds...")
        # sleep(2)

        # Navigate the site and get the loan amount
        amount: str = seek_accounts_data(driver, wait)
        amount_df: pd.DataFrame = parse_accounts_summary(amount)

        # Get other details/info about the loan
        other_data_keys: List[WebElement]
        other_data_values: List[WebElement]
        other_data_keys, other_data_values = seek_other_data(driver, wait)
        other_data_df: pd.DataFrame = parse_other_data(
            other_data_keys, other_data_values
        )

        # Get the loan number
        loan_number: str = get_loan_number(driver, wait)

        # Merge the loan amount and the other details
        return_table = pd.merge(
            amount_df, other_data_df, left_index=True, right_index=True
        )
        return_table["account_number"]: pd.DataFrame = loan_number
        return_table["account_type"]: pd.DataFrame = "loan"
        return_table["usd_value"]: pd.DataFrame = 1.0
        return_table["Balance"]: pd.DataFrame = pd.to_numeric(return_table["Balance"])

        return_tables.append(return_table)

    # Process tables
    return_table: pd.DataFrame = pd.concat(return_tables)
    return_table["symbol"]: pd.DataFrame = SYMBOL

    return_tables: List[pd.DataFrame] = [return_table]

    return return_tables


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
def wait_for_landing_page(wait: WebDriverWait) -> None:
    """
    Wait for landing page after handling 2FA
    :param wait: WebDriverWait object for the driver
    """
    log.info(f"Waiting for landing page...")
    wait.until(EC.url_to_be(DASHBOARD_PAGE))


def get_accounts_info(
    username: str, password: str, prometheus: bool = False, mfa_auth: MfaAuth = None
) -> Union[List[pd.DataFrame], Tuple[List[PrometheusMetric], List[PrometheusMetric]]]:
    """
    Gets the accounts info for a given user/pass as a list of pandas dataframes
    :param username: Your username for logging in
    :param password: Your password for logging in
    :param prometheus: True/False value for exporting as Prometheus-friendly exposition
    :param mfa_auth: A typed dict containing an int representation of the MFA contact opt. and a dir containing the OTP
    :return: A list of pandas dataframes of accounts info tables
    """
    # Get Driver config
    chrome_options: ChromeOptions = get_chrome_options(CHROME_OPTIONS)

    # Instantiating the Driver
    driver: Chrome = start_chromedriver(chrome_options)
    wait: WebDriverWait = WebDriverWait(driver, TIMEOUT)

    # Navigate to the logon page and submit credentials
    logon(driver, wait, HOMEPAGE, username, password)

    # Handle 2FA if prompted, or quit if Chase catches us
    if is_mfa_redirect(driver):
        handle_multi_factor_authentication(driver, wait, mfa_auth)

    # Wait for landing page after handling 2FA
    wait_for_landing_page(wait)

    # Scrape the loan data ready for output
    return_tables: List[pd.DataFrame] = scrape_loan_data(driver, wait)

    # Clean up
    driver.quit()

    # Convert to Prometheus exposition if flag is set
    if prometheus:
        balances: List[PrometheusMetric] = convert_to_prometheus(
            return_tables,
            INSTITUTION,
            "account_number",
            "symbol",
            "Balance",
            "account_type",
        )

        asset_values: List[PrometheusMetric] = convert_to_prometheus(
            return_tables,
            INSTITUTION,
            "account_number",
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
