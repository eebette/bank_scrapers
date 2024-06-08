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
from datetime import datetime

# Non-Standard Imports
import pandas as pd
from selenium.webdriver.common.by import By

# Local Imports
from bank_scrapers.scrapers.common.functions import *
from bank_scrapers.common.functions import convert_to_prometheus, search_files_for_int, search_for_dir

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
ERROR_DIR: str = search_for_dir(__file__, "errors")


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}.png")
def handle_multi_factor_authentication(
    driver: Chrome, wait: WebDriverWait, mfa_auth=None
) -> None:
    """
    Navigates the MFA workflow for this website
    :param driver: The Chrome driver/browser used for this function
    :param wait: The wait object associated with the driver function above
    :param mfa_auth:
    """
    # Identify MFA options
    options: List[WebElement] = wait_and_find_elements(
        driver, wait, (By.XPATH, "//div[@id='otpOption']//input[@type='radio']")
    )

    labels: List[WebElement] = wait_and_find_elements(
        driver, wait, (By.XPATH, "//div[@id='otpOption']//label[@class='mdc-label']")
    )

    # Prompt user input for MFA option
    if mfa_auth is None:
        for i, l in enumerate(labels):
            print(f"{i + 1}: {l.text}")
        o_index: int = int(input("Please select one: ")) - 1
    else:
        o_index: int = mfa_auth["otp_contact_option"] - 1

    # Click based on user input
    mfa_option: WebElement = options[o_index]
    mfa_option.click()

    submit: WebElement = wait_and_find_click_element(
        driver, wait, (By.XPATH, "//bki-one-time-pin-verify//button[@type='submit']")
    )
    submit.click()

    otp: WebElement = wait_and_find_element(
        driver, wait, (By.XPATH, "//bki-one-time-pin-verify//input[@name='otpInput']")
    )
    if mfa_auth is None:
        otp_code: str = input("Enter 2FA Code: ")
    else:
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
    otp.send_keys(otp_code)

    submit: WebElement = wait_and_find_element(
        driver, wait, (By.XPATH, "//bki-one-time-pin-verify//button[@type='submit']")
    )
    driver.execute_script("arguments[0].click();", submit)

    sleep(5)

    close: WebElement = wait_and_find_element(
        driver, wait, (By.XPATH, "//bki-one-time-pin-verify//button[@type='submit']")
    )
    driver.execute_script("arguments[0].click();", close)


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


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}.png")
def logon(
    driver: Chrome,
    wait: WebDriverWait,
    homepage: str,
    username: str,
    password: str,
    mfa_auth=None,
) -> None:
    """
    Opens and signs on to an account
    :param driver: The browser application
    :param wait: WebDriverWait object for the driver
    :param homepage: The logon url to initially navigate
    :param username: Your username for logging in
    :param password: Your password for logging in
    :param mfa_auth:
    """
    # Logon Page
    driver.get(homepage)

    # Enter User
    user: WebElement = wait_and_find_element(driver, wait, (By.ID, "username"))
    user.send_keys(username)

    # Enter Password
    passwd: WebElement = wait_and_find_element(driver, wait, (By.ID, "password"))
    passwd.send_keys(password)

    # TOS
    tos: WebElement = wait_and_find_element(driver, wait, (By.ID, "agreeToTerms-input"))
    driver.execute_script("arguments[0].click();", tos)

    # Submit credentials
    submit: WebElement = wait_and_find_click_element(
        driver, wait, (By.XPATH, "//button[@type='submit'][1]")
    )
    driver.execute_script("arguments[0].click();", submit)

    # Wait for redirect to landing page or 2FA
    wait.until(
        lambda _: DASHBOARD_PAGE in driver.current_url or is_mfa_redirect(driver)
    )

    # Handle 2FA if prompted, or quit if Chase catches us
    if is_mfa_redirect(driver):
        handle_multi_factor_authentication(driver, wait, mfa_auth)

    # Wait for landing page after handling 2FA
    wait.until(EC.url_to_be(DASHBOARD_PAGE))


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}.png")
def seek_accounts_data(driver: Chrome, wait: WebDriverWait) -> str:
    """
    Navigate the website and click download button for the accounts data
    :param driver: The Chrome browser application
    :param wait: WebDriverWait object for the driver
    """
    amount: str = wait_and_find_element(driver, wait, (By.CLASS_NAME, "amount")).text
    return amount


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}.png")
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


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}.png")
def get_loan_number(driver: Chrome, wait: WebDriverWait) -> str:
    """
    Gets the full loan number from the My Loan page on the RoundPoint website
    :param driver: The Chrome browser application
    :param wait: WebDriverWait object for the driver
    :return: The full loan number as a string
    """
    # Navigate to the My Loan page
    driver.get(
        "https://loansphereservicingdigital.bkiconnect.com/servicinghome/#/my-loan"
    )

    # Find the element for the loan number
    loan_number_element: WebElement = wait_and_find_element(
        driver, wait, (By.XPATH, "//bki-myloan-balance//a[@class='card-link']")
    )

    # Click so that the full loan number is exposed
    loan_number_element.click()

    # Get the loan number
    loan_number: str = wait_and_find_element(
        driver, wait, (By.XPATH, "//bki-myloan-balance//span[@isolate='']")
    ).text

    # Return the loan number
    return loan_number


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}.png")
def scrape_loan_data(driver: Chrome, wait: WebDriverWait) -> List[pd.DataFrame]:
    """
    Iterates through the account's loans and processes the data into a list of Pandas DataFrames
    :param driver: The Chrome browser application
    :param wait: WebDriverWait object for the driver
    :return: A list of Pandas DataFrames containing the loans data
    """
    # Find and expand the dropdown list containing the account's loans
    loans_button: WebElement = wait_and_find_element(
        driver, wait, (By.XPATH, "//div[@class='secondary-header-top']//button")
    )
    loans_button.click()

    # Get the list of loans in the dropdown list
    loans: List[WebElement] = wait_and_find_elements(
        driver,
        wait,
        (By.XPATH, "//div[@id='loanMenuId']//div[contains(@class, 'cursor')]"),
    )

    return_tables: List = list()
    for loan in loans:
        # Go back to dashboard page if not there already
        if driver.current_url != DASHBOARD_PAGE:
            driver.get(DASHBOARD_PAGE)

        # Must click twice to expand list
        wait.until(EC.element_to_be_clickable(loans_button))
        loans_button.click()
        loans_button.click()

        # Click on the next loan
        wait.until(EC.element_to_be_clickable(loan))
        loan.click()
        sleep(2)

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

        return_tables.append(return_table)

    # Process tables
    return_table: pd.DataFrame = pd.concat(return_tables)
    return_table["symbol"]: pd.DataFrame = SYMBOL

    return_tables: List[pd.DataFrame] = [return_table]

    return return_tables


def get_accounts_info(
    username: str, password: str, prometheus: bool = False, mfa_auth=None
) -> List[pd.DataFrame] | List[Tuple[List, float]]:
    """
    Gets the accounts info for a given user/pass as a list of pandas dataframes
    :param username: Your username for logging in
    :param password: Your password for logging in
    :param prometheus: True/False value for exporting as Prometheus-friendly exposition
    :param mfa_auth:
    :return: A list of pandas dataframes of accounts info tables
    """
    # Get Driver config
    chrome_options: ChromeOptions = get_chrome_options(CHROME_OPTIONS)

    # Instantiating the Driver
    driver: Chrome = start_chromedriver(chrome_options)
    wait: WebDriverWait = WebDriverWait(driver, TIMEOUT)

    # Navigate to the logon page and submit credentials
    logon(driver, wait, HOMEPAGE, username, password, mfa_auth)

    # Scrape the loan data ready for output
    return_tables: List[pd.DataFrame] = scrape_loan_data(driver, wait)

    # Clean up
    driver.quit()

    # Convert to Prometheus exposition if flag is set
    if prometheus:
        return_tables: List[Tuple[List, float]] = convert_to_prometheus(
            return_tables,
            INSTITUTION,
            "account_number",
            "symbol",
            "Balance",
            "account_type",
        )

    # Return list of pandas df
    return return_tables
