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
from typing import List, Tuple, Dict, Union
from datetime import datetime
from time import sleep
import re

# Non-Standard Imports
import pandas as pd
from selenium.webdriver.remote.webelement import WebElement, ShadowRoot
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from undetected_chromedriver import Chrome, ChromeOptions
from pyvirtualdisplay import Display

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
    wait_and_find_element_in_shadow_root,
    wait_and_find_elements_in_shadow_root,
    wait_and_find_click_element,
    screenshot_on_timeout,
)
from bank_scrapers.scrapers.chase.mfa_auth import ChaseMfaAuth

# Institution info
INSTITUTION: str = "Chase"
SYMBOL: str = "USD"

# Logon page
HOMEPAGE: str = "https://www.chase.com/personal/credit-cards/login-account-access"

# Timeout
TIMEOUT: int = 60

# Chrome config
USER_AGENT: str = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.50 Safari/537.36"
)
CHROME_OPTIONS: List[str] = [
    f"user-agent={USER_AGENT}",
    "--no-sandbox",
    "--window-size=1920,1080",
    "--disable-gpu",
    "--allow-running-insecure-content",
]

# Error screenshot config
ERROR_DIR: str = f"{ROOT_DIR}/errors"


def check_element_is_ineligible(
    element: WebElement,
    ineligibility_check_xpath: str,
    ineligibility_check_attribute: str,
) -> bool:
    """
    Checks if a WebElement has an eligibility flag set based on provided relative XPath and attribute
    :param element: The WebElement for which to check eligibility
    :param ineligibility_check_xpath: XPath value to a WebElement that can be used to check if the element is ineligible
    :param ineligibility_check_attribute: Attribute value within a WebElement (set with XPath) that can be used
    to check if the element is ineligible
    :return: Boolean value True if the element is ineligible, False is not ineligible
    """
    try:
        # Check if ineligibility flag is set, if not assume label is eligible/not disabled
        is_disabled: bool = bool(
            element.find_element(By.XPATH, ineligibility_check_xpath).get_attribute(
                ineligibility_check_attribute
            )
        )
    except NoSuchElementException:
        is_disabled: bool = False
        pass

    return is_disabled


def _split_list_into_chunks(input_list: List, n: int):
    """
    Splits a list into n equal size chunks
    :param input_list: The original list to split
    :param n: Number of output lists (chunks) to split the list into
    :return: A list of chunked lists
    """
    split_list: List[List] = [
        input_list[i : i + n] for i in range(0, len(input_list), n)
    ]
    return split_list


def _organize_headers_with_labels(
    headers: List[WebElement],
    labels: List[WebElement],
    label_ineligibility_check_xpath: str = None,
    label_ineligibility_check_attribute: str = None,
    text_to_display: str = "innerText",
) -> Tuple[List[Tuple[str, int]], List[WebElement]]:
    """
    Takes a list of headers (titles) Web Elements and a list of label Web Elements and creates a human-readable list of
    options. This function assumes that the labels are organized such that the first n elements belong to the first
    header, the second n elements belong to the second header, and so on (where n equals the count of all elements
    divided by the number of headers). Also returns an ordered concatenated list of headers and labels
    :param headers: List of WebElements containing the headers (titles) which precede labels in the list
    :param labels: List of WebElements containing the labels which proceed the headers in the list
    :param label_ineligibility_check_xpath: XPath value to a WebElement that can be used to check if a list label
    (option) is ineligible
    :param label_ineligibility_check_attribute: Attribute value within a WebElement (set with XPath) that can be used
    to check if a list label (option) is ineligible
    :param text_to_display: Text value to pull from the headers/labels WebElements to use for the human-readable output
    string
    :return: A tuple containing 1: a list of
    tuples containing a: a string of human-readable eligible options (titles + labels), and b: an integer representing
    the index of the corresponding WebElement for that option in the unified ordered list mentioned below, and 2: a
    unified ordered list of WebElements for the headers and labels
    """
    # Making the OTP options human-readable
    n: int = int(len(labels) / len(headers))

    # Split the labels into equal numbers groups based on the number of headers
    split_labels: List[List[WebElement]] = _split_list_into_chunks(labels, n)

    output_list: List[Tuple[str, int]] = list()
    headers_with_labels: List[WebElement] = list()

    # Iterate through headers and add each header to the concatenated list (followed by its labels)
    for i, header in enumerate(headers):
        headers_with_labels.append(header)

        # Iterate through the labels, labelling each label with its index in the full headers + labels list and
        # formatting it as a human-readable output
        for label in split_labels[i]:
            original_index: int = len(headers_with_labels)
            headers_with_labels.append(label)

            # Check if label is ineligible
            is_disabled: bool = check_element_is_ineligible(
                label,
                label_ineligibility_check_xpath,
                label_ineligibility_check_attribute,
            )
            if not is_disabled:
                # Append human-readable label and original index for easily reconciling with full list of all
                # WebElements
                output_list.append(
                    (
                        f"{header.get_attribute(text_to_display)}: {label.get_attribute(text_to_display)}",
                        original_index,
                    )
                )
    return output_list, headers_with_labels


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
def handle_multi_factor_authentication(
    driver: Chrome, wait: WebDriverWait, password: str, mfa_auth: ChaseMfaAuth = None
) -> None:
    """
    Navigates the MFA workflow for this website
    Note that this function only covers Email Me options for now.
    :param driver: The Chrome driver/browser used for this function
    :param wait: The wait object associated with the driver function above
    :param password: User's password to enter along with OTP
    :param mfa_auth: A typed dict containing an int representation of the MFA contact opt. and a dir containing the OTP Typed Dict with MFA inputs for automation
    """
    log.info(f"Redirected to traditional two-factor authentication page.")

    # Wait for the expand option to become clickable or else can lead to bugs where the list doesn't expand correctly
    log.info(
        f"Finding list expand button element and waiting for it to be clickable..."
    )
    expand_button: WebElement = wait_and_find_click_element(
        driver, wait, (By.ID, "header-simplerAuth-dropdownoptions-styledselect")
    )

    # Then click it
    log.info(f"Clicking list expand button element...")
    expand_button.click()
    sleep(1)

    # Identify MFA options
    log.info(f"Finding contact options elements...")
    contact_options: List[WebElement] = wait_and_find_elements(
        driver,
        wait,
        (By.XPATH, '//a[@role="option"]/span[@class="groupLabelText primary"]'),
    )

    log.info(f"Finding labels for contact options elements...")
    labels: List[WebElement] = wait_and_find_elements(
        driver,
        wait,
        (By.XPATH, '//a[@role="option"]/span[@class="primary groupingName"]'),
    )

    # Making the OTP options human-readable
    output_list: List[Tuple[str, int]]
    full_labels: List[WebElement]
    output_list, full_labels = _organize_headers_with_labels(
        contact_options, labels, "./..", "aria-disabled"
    )

    # Prompt user input for MFA option
    if mfa_auth is None:
        log.info(f"No automation info provided. Prompting user for contact option.")
        for i, l in enumerate(output_list):
            print(f"{i + 1}: {l[0]}")
        option: str = input("Please select one: ")
    else:
        log.info(f"Contact option found in automation info.")
        option: str = str(mfa_auth["otp_contact_option"])
    l_index: int = output_list[int(option) - 1][1]
    log.debug(f"Contact option: {l_index}")

    # Click based on user input
    log.info(f"Clicking list expand button element...")
    expand_button.click()

    log.info(
        f"Finding element for user selected contact option and waiting for it to be clickable..."
    )
    mfa_option: WebElement = wait.until(
        EC.element_to_be_clickable(full_labels[l_index])
    )

    log.info(f"Clicking element for user selected contact option...")
    mfa_option.click()

    # Click submit once it becomes clickable
    log.info(f"Finding submit button element and waiting for it to be clickable...")
    submit: WebElement = wait_and_find_click_element(
        driver, wait, (By.XPATH, "//button[@id='requestIdentificationCode-sm']")
    )

    log.info(f"Clicking submit button element...")
    submit.click()

    # Prompt user for OTP code and enter onto the page
    log.info(f"Finding input box element for OTP...")
    otp_input: WebElement = wait_and_find_element(
        driver, wait, (By.XPATH, "//input[@id='otpcode_input-input-field']")
    )

    # Prompt user input for MFA option
    if mfa_auth is None:
        log.info(f"No automation info provided. Prompting user for OTP.")
        otp_code: str = input("Enter OTP Code: ")
    else:
        log.info(
            f"OTP file location found in automation info: {mfa_auth["otp_code_location"]}"
        )
        otp_code: str = str(
            search_files_for_int(
                mfa_auth["otp_code_location"], INSTITUTION, ".txt", 6, 10, TIMEOUT, True
            )
        )

    log.info(f"Sending info to OTP input box element...")
    otp_input.send_keys(otp_code)

    # Re-enter the password on the OTP page
    log.info(f"Finding password element...")
    pwd_input: WebElement = wait_and_find_element(
        driver, wait, (By.XPATH, "//input[@id='password_input-input-field']")
    )

    log.info(f"Sending info to password element...")
    pwd_input.send_keys(password)

    # Click submit once it becomes clickable
    log.info(f"Finding submit button element and waiting for it to be clickable...")
    submit: WebElement = wait_and_find_click_element(
        driver, wait, (By.XPATH, "//input[@id='log_on_to_landing_page-sm']")
    )

    log.info(f"Clicking submit button element...")
    submit.click()


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
def handle_multi_factor_authentication_alternate(
    driver: Chrome, wait: WebDriverWait, mfa_auth: ChaseMfaAuth = None
) -> None:
    """
    Navigates the MFA workflow for this website
    Note that this function only covers Email Me options for now.
    :param driver: The Chrome driver/browser used for this function
    :param wait: The wait object associated with the driver function above
    :param mfa_auth: A typed dict containing an int representation of the MFA contact opt. and a dir containing the OTP
    """
    log.info(f"Redirected to two-factor authentication page.")

    # Identify MFA options
    log.info(f"Finding contact options elements...")
    contact_options: List[WebElement]
    contact_options_wait: WebDriverWait
    contact_options, contact_options_wait = wait_and_find_elements_in_shadow_root(
        driver,
        wait,
        (By.XPATH, "//mds-list[@id='optionsList']"),
        TIMEOUT,
        (By.CSS_SELECTOR, "li"),
    )

    contact_options_text: List[str] = []
    for contact_option in contact_options:
        contact_options_text.append(
            wait_and_find_element(
                contact_option,
                contact_options_wait,
                (By.CSS_SELECTOR, "label"),
            ).text
        )

    # Prompt user input for MFA option
    if mfa_auth is None:
        log.info(f"No automation info provided. Prompting user for contact option.")
        for i, l in enumerate(contact_options_text):
            print(f"{i + 1}: {l}")
        option: str = input("Please select one: ")
    else:
        log.info(f"Contact option found in automation info.")
        option: str = str(mfa_auth["otp_contact_option_alternate"])
    l_index: int = int(option) - 1
    log.debug(f"Contact option: {l_index}")

    # Click based on user input
    contact_options[l_index].click()

    # Open accounts dropdown
    log.info(f"Finding next button element...")
    next_button: WebElement
    next_button_wait: WebDriverWait
    next_button, next_button_wait = wait_and_find_element_in_shadow_root(
        driver,
        wait,
        (By.XPATH, "//mds-button[@text='Next']"),
        TIMEOUT,
        (By.CSS_SELECTOR, "button"),
    )

    log.info(f"Waiting for next button element to be clickable...")
    next_button_wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button")))

    log.info(f"Clicking next button element...")
    next_button.click()

    # Prompt user for OTP code and enter onto the page
    log.info(f"Finding input box element for OTP...")
    otp_input: WebElement
    otp_input, _ = wait_and_find_element_in_shadow_root(
        driver,
        wait,
        (By.XPATH, "//mds-text-input-secure"),
        TIMEOUT,
        (By.CSS_SELECTOR, "input"),
    )

    # Prompt user input for MFA option
    if mfa_auth is None:
        log.info(f"No automation info provided. Prompting user for OTP.")
        otp_code: str = input("Enter OTP Code: ")
    else:
        log.info(
            f"OTP file location found in automation info: {mfa_auth["otp_code_location"]}"
        )
        otp_code: str = str(
            search_files_for_int(
                mfa_auth["otp_code_location"], INSTITUTION, ".txt", 6, 10, TIMEOUT, True
            )
        )

    log.info(f"Sending info to OTP input box element...")
    otp_input.send_keys(otp_code)

    # Click submit once it becomes clickable
    log.info(f"Finding submit button element...")
    submit: WebElement
    submit_wait: WebDriverWait
    submit, submit_wait = wait_and_find_element_in_shadow_root(
        driver,
        wait,
        (By.XPATH, "//mds-button[@text='Next']"),
        TIMEOUT,
        (By.CSS_SELECTOR, "button"),
    )

    log.info(f"Waiting for submit button element to be clickable...")
    submit_wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button")))

    log.info(f"Clicking submit button element...")
    submit.click()


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
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
    log.info(f"Accessing: {homepage}")
    driver.get(homepage)

    # Navigate iframe
    log.info(f"Finding iframe for login...")
    iframe: WebElement = wait_and_find_element(
        driver, wait, (By.XPATH, "//iframe[@id='routablecpologonbox']")
    )

    log.info(f"Switching to iframe...")
    driver.switch_to.frame(iframe)

    # Enter User
    log.info(f"Finding username element and waiting for it to be clickable...")
    log.debug(f"Username: {username}")
    user: WebElement = wait_and_find_click_element(
        driver, wait, (By.XPATH, "//input[@id='userId-text-input-field']")
    )

    log.info(f"Clicking username element...")
    user.click()

    log.info(f"Sending info to username element...")
    log.debug(f"Username: {username}")
    user.send_keys(username)

    # Enter Password
    log.info(f"Finding password element...")
    passwd: WebElement = wait_and_find_element(
        driver, wait, (By.XPATH, "//input[@id='password-text-input-field']")
    )

    log.info(f"Sending info to password element...")
    passwd.send_keys(password)

    # Submit will sometimes stay inactive unless interacted with
    log.info(f"Finding submit button element...")
    submit: WebElement = wait_and_find_element(
        driver, wait, (By.XPATH, "//button[@id='signin-button']")
    )

    log.info(f"Sending dummy key to submit button element...")
    submit.send_keys("")

    log.info(f"Waiting for submit button element to be clickable...")
    wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@id='signin-button']")))

    log.info(f"Clicking submit button element...")
    submit.click()


# noinspection PyTypeChecker
@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
def seek_accounts_data(driver: Chrome, wait: WebDriverWait) -> None:
    """
    Navigate the website and click download button for the accounts data
    :param driver: The Chrome browser application
    :param wait: WebDriverWait object for the driver
    """
    # Navigate shadow root
    log.info(f"Finding shadow root for accounts dropdown element...")
    shadow_root: ShadowRoot = wait_and_find_element(
        driver, wait, (By.XPATH, "//mds-button[@text='More']")
    ).shadow_root
    sr_wait: WebDriverWait = WebDriverWait(shadow_root, TIMEOUT)

    # Open accounts dropdown
    log.info(f"Finding accounts dropdown element...")
    accounts_dropdown: WebElement = wait_and_find_element(
        shadow_root, sr_wait, (By.CSS_SELECTOR, "button")
    )

    log.info(f"Clicking accounts dropdown element...")
    accounts_dropdown.click()

    # Navigate another shadow root
    log.info(f"Finding shadow root for account details element...")
    shadow_root_: ShadowRoot = wait_and_find_element(
        shadow_root, sr_wait, (By.CSS_SELECTOR, "mds-menu-button-overlay")
    ).shadow_root
    sr_wait_: WebDriverWait = WebDriverWait(shadow_root_, TIMEOUT)

    # Wait for the account details button to be clickable and go to it
    log.info(
        f"Finding button for account details element and waiting for it to be clickable..."
    )
    btn: WebElement = wait_and_find_click_element(
        shadow_root_,
        sr_wait_,
        (By.CSS_SELECTOR, "button[aria-label='Account details']"),
    )
    log.info(f"Clicking button for account details element...")
    btn.click()


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
def parse_accounts_summary(table: WebElement) -> pd.DataFrame:
    """
    Takes a table as a web element from the Chase accounts overview page and turns it into a pandas df
    :param table: The table as a web element
    :return: A pandas dataframe of the table
    """
    #  Transpose vertical headers labels
    dt: List[WebElement] = table.find_elements(By.XPATH, ".//dt")
    dt_txt: List[str] = list(d.text for d in dt)

    # Data
    dd: List[WebElement] = table.find_elements(By.XPATH, ".//dd")
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

    # Make sure that balance column is numeric
    if "Current balance" in df.columns:
        df["Current balance"]: pd.DataFrame = pd.to_numeric(df["Current balance"])

    return df


def is_mfa_redirect(driver: Chrome) -> bool:
    """
    Checks and determines if the site is forcing MFA on the login attempt
    :param driver: The Chrome browser application
    :return: True if MFA is being enforced
    """
    if (
        "chase.com/web/auth/" in driver.current_url
        and "We don't recognize this device" in driver.page_source
    ):
        return True
    else:
        return False


def is_mfa_redirect_alternate(driver: Chrome) -> bool:
    """
    Checks and determines if the site is forcing MFA on the login attempt
    :param driver: The Chrome browser application
    :return: True if MFA is being enforced
    """
    if (
        "chase.com/web/auth/" in driver.current_url
        and "Let's make sure it's you" in driver.page_source
    ):
        return True
    else:
        return False


def password_needs_reset(driver: Chrome) -> bool:
    """
    Checks if Chase is forcing a password change as a result of too many failed login attempts
    :param driver: The Chrome browser application
    :return: True if password needs reset
    """
    if (
        "chase.com/web/auth/" in driver.current_url
        and "We can't find that username and password" in driver.page_source
        and "Keep in mind: You won't be able to see your statements and notices until you reset your password."
        in driver.page_source
    ):
        return True
    else:
        return False


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
def wait_for_redirect(driver: Chrome, wait: WebDriverWait) -> None:
    """
    Wait for the page to redirect to the next stage of the login process
    :param driver: The browser application
    :param wait: WebDriverWait object for the driver
    """
    # Wait for redirect to landing page or 2FA
    log.info(f"Handling redirect...")
    wait.until(
        lambda _: "chase.com/web/auth/dashboard#/dashboard/overview"
        in driver.current_url
        or is_mfa_redirect(driver)
        or is_mfa_redirect_alternate(driver)
        or password_needs_reset(driver)
    )


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
def wait_for_landing_page(driver: Chrome, wait: WebDriverWait) -> None:
    """
    Wait for landing page after handling 2FA
    :param driver: The browser application
    :param wait: WebDriverWait object for the driver
    """
    log.info(f"Waiting for landing page...")
    wait.until(
        lambda _: "chase.com/web/auth/dashboard#/dashboard/overview"
        in driver.current_url
    )


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
def get_account_number(driver: Chrome, wait: WebDriverWait) -> str:
    """
    Gets the account number from the credit card details page
    :param driver: The browser application
    :param wait: WebDriverWait object for the driver
    :return: A string containing the account number
    """
    log.info(f"Finding account number element...")

    account_number_xpath: str = (
        "//h2[contains(@class, 'accountdetails')]/span[contains(@class, 'mask-number')]"
    )
    account_number: str = wait_and_find_element(
        driver, wait, (By.XPATH, account_number_xpath)
    ).text

    log.debug(f"Account number (raw): {account_number}")
    account_number: str = re.sub("[^0-9]", "", account_number)

    return account_number


@screenshot_on_timeout(f"{ERROR_DIR}/{datetime.now()}_{INSTITUTION}.png")
def get_detail_tables(driver: Chrome, wait: WebDriverWait) -> List[WebElement]:
    """
    Gets the web elements for the tables containing the account details for each account
    :param driver: The browser application
    :param wait: WebDriverWait object for the driver
    :return: A list containing the web elements for the tables
    """
    log.info(f"Finding account details elements...")
    tables: List[WebElement] = wait_and_find_elements(
        driver, wait, (By.XPATH, "//dl[contains(@class, 'details-bar')]")
    )
    return tables


def get_accounts_info(
    username: str,
    password: str,
    prometheus: bool = False,
    mfa_auth: ChaseMfaAuth = None,
) -> Union[List[pd.DataFrame], Tuple[List[PrometheusMetric], List[PrometheusMetric]]]:
    """
    Gets the accounts info for a given user/pass as a list of pandas dataframes
    :param username: Your username for logging in
    :param password: Your password for logging in
    :param prometheus: True/False value for exporting as Prometheus-friendly exposition
    :param mfa_auth: A typed dict containing an int representation of the MFA contact opt. and a dir containing the OTP
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
    logon(driver, wait, HOMEPAGE, username, password)

    # Wait to be redirected to the next stage of the login process
    wait_for_redirect(driver, wait)

    # Handle MFA if prompted, or quit if Chase catches us
    if is_mfa_redirect(driver):
        handle_multi_factor_authentication(driver, wait, password, mfa_auth)
    elif is_mfa_redirect_alternate(driver):
        handle_multi_factor_authentication_alternate(driver, wait, mfa_auth)
    elif password_needs_reset(driver):
        log.error("Password needs reset!")
        exit(1)

    # Wait for landing page after handling 2FA
    wait_for_landing_page(driver, wait)

    # Navigate the site and download the accounts data
    seek_accounts_data(driver, wait)

    # Get the account number from the current page
    account_number: str = get_account_number(driver, wait)

    # Process tables
    tables: List[WebElement] = get_detail_tables(driver, wait)
    return_tables: List = list()
    for t in tables:
        parsed_table: pd.DataFrame = parse_accounts_summary(t)
        parsed_table["account"]: pd.DataFrame = account_number
        parsed_table["account_type"]: pd.DataFrame = "credit"
        parsed_table["symbol"]: pd.DataFrame = SYMBOL
        if "Current balance" in parsed_table.columns:
            parsed_table["usd_value"]: pd.DataFrame = 1.0
        return_tables.append(parsed_table)

    # Clean up
    driver.quit()

    # Convert to Prometheus exposition if flag is set
    if prometheus:
        balances: List[PrometheusMetric] = convert_to_prometheus(
            return_tables,
            INSTITUTION,
            "account",
            "symbol",
            "Current balance",
            "account_type",
        )

        asset_values: List[PrometheusMetric] = convert_to_prometheus(
            return_tables,
            INSTITUTION,
            "account",
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
