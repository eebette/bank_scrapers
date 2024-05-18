"""
This file provides the get_accounts_info() function for BECU (https://onlinebanking.becu.org)

Example Usage:
```
tables = get_accounts_info(username="{username}", password="{password}")
for t in tables:
    print(t.to_string())
```
"""

# Standard library imports
from typing import Dict

# Non-Standard Imports
import pandas as pd
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from prometheus_client import CollectorRegistry, write_to_textfile

# Local Imports
from bank_scrapers.scrapers.common.functions import *
from bank_scrapers.common.functions import convert_to_prometheus

# Institution info
INSTITUTION: str = "BECU"
SYMBOL: str = "USD"

# Logon page
HOMEPAGE: str = "https://onlinebanking.becu.org/BECUBankingWeb/Login.aspx"

# Timeout
TIMEOUT: int = 10

# Chrome config
USER_AGENT: str = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.50 Safari/537.36"
)
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


def get_mfa_answer(
    driver: Chrome, wait: WebDriverWait, mfa_answers: Dict[str, str] | None = None
) -> str:
    """
    Returns the answer for the MFA question or prompts the user for the answer if not provided
    :param driver: The browser application
    :param wait: WebDriverWait object for the driver
    :param mfa_answers: A dict of the MFA answers where the keys are the questions and the values are the answers
    :return: The MFA answer to input
    """
    mfa_question: WebElement = wait_and_find_element(
        driver, wait, (By.XPATH, "//label[@for='challengeAnswer']")
    )

    if mfa_answers is not None:
        mfa_answer: str = mfa_answers[mfa_question.text]
    else:
        # Prompt user input for MFA option
        print(mfa_question.text)
        mfa_answer: str = input("Please provide an answer: ")

    return mfa_answer


def handle_redirect(wait: WebDriverWait) -> None:
    """
    Waits until the page redirects to account home, marketing/offer page, or MFA page
    :param wait:
    """
    wait.until(
        lambda driver: any(
            driver.current_url in landing_page
            for landing_page in [
                "https://onlinebanking.becu.org/BECUBankingWeb/Accounts/Summary.aspx",
                "https://onlinebanking.becu.org/BECUBankingWeb/Invitation/Default.aspx",
                "https://onlinebanking.becu.org/BECUBankingWeb/Security/Challenge",
            ]
        )
    )


def logon(
    driver: Chrome,
    wait: WebDriverWait,
    homepage: str,
    username: str,
    password: str,
    mfa_answers: Dict[str, str] | None = None,
) -> None:
    """
    Opens and signs on to an account
    :param driver: The browser application
    :param wait: WebDriverWait object for the driver
    :param homepage: The logon url to initially navigate
    :param username: Your username for logging in
    :param password: Your password for logging in
    :param mfa_answers:
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

    while (
        driver.current_url
        != "https://onlinebanking.becu.org/BECUBankingWeb/Accounts/Summary.aspx"
    ):
        # Wait for redirect to landing page
        handle_redirect(wait)

        if (
            driver.current_url
            == "https://onlinebanking.becu.org/BECUBankingWeb/Invitation/Default.aspx"
        ):
            # Decline offer
            decline_btn: WebElement = wait_and_find_element(
                driver, wait, (By.NAME, "ctlWorkflow$decline")
            )
            decline_btn.click()

        elif (
            driver.current_url
            == "https://onlinebanking.becu.org/BECUBankingWeb/Security/Challenge"
        ):
            # Get MFA answer
            mfa_answer: str = get_mfa_answer(driver, wait, mfa_answers)

            # Find input box and input MFA answer
            answer_input: WebElement = wait_and_find_element(
                driver, wait, (By.ID, "challengeAnswer")
            )
            answer_input.send_keys(mfa_answer)

            # Find agree/submit button and click
            agree_input: WebElement = wait_and_find_element(
                driver, wait, (By.ID, "agree-and-continue-button")
            )
            agree_input.click()


def get_accounts_info(
    username: str, password: str, prometheus: bool = False
) -> List[pd.DataFrame] | List[Tuple[List, float]]:
    """
    Gets the accounts info for a given user/pass as a list of pandas dataframes
    :param username: Your username for logging in
    :param password: Your password for logging in
    :param prometheus: True/False value to exporting as Prometheus-friendly exposition
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
    wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//tbody[@id='visaTable']/tr[@class='item']")
        )
    )

    # Process tables
    return_tables: List = list()
    for t in tables:
        table: pd.DataFrame = process_table(t)
        is_credit_account = any(
            list(True for header in table.columns if "credit" in header.lower())
        )
        table.name = "credit" if is_credit_account else "deposit"
        return_tables.append(table)

    # Clean up
    driver.quit()

    # Convert to Prometheus exposition if flag is set
    if prometheus:
        return_tables: List[Tuple[List, float]] = convert_to_prometheus(
            return_tables, INSTITUTION, "Account", SYMBOL, "Current Balance"
        )

    # Return list of pandas df
    return return_tables
