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
import re
from time import sleep

# Non-Standard Imports
import pandas as pd
from selenium.webdriver.common.by import By
from pyvirtualdisplay import Display

# Local Imports
from bank_scrapers import ROOT_DIR
from bank_scrapers.common.functions import convert_to_prometheus, search_files_for_int
from bank_scrapers.scrapers.common.functions import screenshot_on_timeout
from bank_scrapers.scrapers.common.functions import *

# Institution info
INSTITUTION: str = "Chase"
SYMBOL: str = "USD"

# Logon page
HOMEPAGE: str = "https://www.chase.com/personal/credit-cards/login-account-access"

# Timeout
TIMEOUT: int = 60

# Chrome config
CHROME_OPTIONS: List[str] = [
    "--no-sandbox",
    "--window-size=1920,1080",
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


@screenshot_on_timeout(f"{ROOT_DIR}/errors/{datetime.now()}.png")
def handle_multi_factor_authentication(
    driver: Chrome, wait: WebDriverWait, password: str, mfa_auth=None
) -> None:
    """
    Navigates the MFA workflow for this website
    Note that this function only covers Email Me options for now.
    :param driver: The Chrome driver/browser used for this function
    :param wait: The wait object associated with the driver function above
    :param password: User's password to enter along with OTP
    :param mfa_auth: Typed Dict with MFA inputs for automation
    """

    # Wait for the expand option to become clickable or else can lead to bugs where the list doesn't expand correctly
    expand_button: WebElement = wait_and_find_click_element(
        driver, wait, (By.ID, "header-simplerAuth-dropdownoptions-styledselect")
    )

    # Then click it
    expand_button.click()
    sleep(1)

    # Identify MFA options
    contact_options: List[WebElement] = wait_and_find_elements(
        driver,
        wait,
        (By.XPATH, '//a[@role="option"]/span[@class="groupLabelText primary"]'),
    )

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
        for i, l in enumerate(output_list):
            print(f"{i + 1}: {l[0]}")
        option: str = input("Please select one: ")
    else:
        option: str = mfa_auth["otp_contact_option"]
    l_index: int = output_list[int(option) - 1][1]

    # Click based on user input
    expand_button.click()
    mfa_option: WebElement = wait.until(
        EC.element_to_be_clickable(full_labels[l_index])
    )
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

    # Prompt user input for MFA option
    if mfa_auth is None:
        otp_code: str = input("Enter 2FA Code: ")
    else:
        otp_code: str = str(
            search_files_for_int(
                mfa_auth["otp_code_location"], INSTITUTION, ".txt", 6, 10, TIMEOUT, True
            )
        )

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


@screenshot_on_timeout(f"{ROOT_DIR}/errors/{datetime.now()}.png")
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


# noinspection PyTypeChecker
@screenshot_on_timeout(f"{ROOT_DIR}/errors/{datetime.now()}.png")
def seek_accounts_data(driver: Chrome, wait: WebDriverWait) -> None:
    """
    Navigate the website and click download button for the accounts data
    :param driver: The Chrome browser application
    :param wait: WebDriverWait object for the driver
    """
    # Navigate shadow root
    shadow_root: ShadowRoot = wait_and_find_element(
        driver, wait, (By.XPATH, "//mds-button[@text='More']")
    ).shadow_root
    sr_wait: WebDriverWait = WebDriverWait(shadow_root, TIMEOUT)

    # Open accounts dropdown
    accounts_dropdown: WebElement = wait_and_find_element(
        shadow_root, sr_wait, (By.CSS_SELECTOR, ".button")
    )
    accounts_dropdown.click()

    # Navigate another shadow root
    sr: ShadowRoot = wait_and_find_element(
        shadow_root, sr_wait, (By.CSS_SELECTOR, ".mds-menu-button--cpo")
    ).shadow_root

    # Wait for the account details button to be clickable and go to it
    sr_wait_: WebDriverWait = WebDriverWait(sr, TIMEOUT)
    btn: WebElement = wait_and_find_click_element(
        sr,
        sr_wait_,
        (By.CSS_SELECTOR, "li.menu-button__list:nth-child(1) > button:nth-child(1)"),
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


def is_2fa_redirect(driver: Chrome):
    """

    :param driver:
    :return:
    """
    if (
        "chase.com/web/auth/" in driver.current_url
        and "We don't recognize this device" in driver.page_source
    ):
        return True


def password_needs_reset(driver: Chrome):
    """

    :param driver:
    :return:
    """
    if (
        "chase.com/web/auth/" in driver.current_url
        and "We can't find that username and password" in driver.page_source
        and "Keep in mind: You won't be able to see your statements and notices until you reset your password."
        in driver.page_source
    ):
        return True


@screenshot_on_timeout(f"{ROOT_DIR}/errors/{datetime.now()}.png")
def wait_for_redirect(driver: Chrome, wait: WebDriverWait) -> None:
    """

    :param driver:
    :param wait:
    :return:
    """
    # Wait for redirect to landing page or 2FA
    wait.until(
        lambda this_driver: "chase.com/web/auth/dashboard#/dashboard/overview"
        in this_driver.current_url
        or is_2fa_redirect(driver)
        or password_needs_reset(driver)
    )


def get_accounts_info(
    username: str, password: str, prometheus: bool = False, mfa_auth=None
) -> List[pd.DataFrame]:
    """
    Gets the accounts info for a given user/pass as a list of pandas dataframes
    :param username: Your username for logging in
    :param password: Your password for logging in
    :param prometheus: True/False value for exporting as Prometheus-friendly exposition
    :param mfa_auth:
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

    wait_for_redirect(driver, wait)

    # Handle 2FA if prompted, or quit if Chase catches us
    if is_2fa_redirect(driver):
        handle_multi_factor_authentication(driver, wait, password, mfa_auth)
    elif password_needs_reset(driver):
        print("Password needs reset!")
        sys.exit(1)

    # Wait for landing page after handling 2FA
    wait.until(
        lambda this_driver: "chase.com/web/auth/dashboard#/dashboard/overview"
        in this_driver.current_url
    )

    # Navigate the site and download the accounts data
    seek_accounts_data(driver, wait)

    account_number: str = wait_and_find_element(
        driver,
        wait,
        (
            By.XPATH,
            "//h2[@class='accountdetails accountname mds-title-medium']/span[@class='mask-number mds-body-large']",
        ),
    ).text
    account_number: str = re.sub("[^0-9]", "", account_number)

    # Process tables
    tables: List[WebElement] = wait_and_find_elements(
        driver, wait, (By.CLASS_NAME, "details-bar")
    )
    return_tables: List = list()
    for t in tables:
        parsed_table: pd.DataFrame = parse_accounts_summary(t)
        parsed_table["account"]: pd.DataFrame = account_number
        parsed_table["account_type"]: pd.DataFrame = "credit"
        parsed_table["symbol"]: pd.DataFrame = SYMBOL
        parsed_table.name = t.find_element(By.XPATH, "./..//h3").text
        return_tables.append(parsed_table)

    # Clean up
    driver.quit()

    # Convert to Prometheus exposition if flag is set
    if prometheus:
        return_tables: List[Tuple[List, float]] = convert_to_prometheus(
            return_tables,
            INSTITUTION,
            "account",
            "symbol",
            "Current balance",
            "account_type",
        )

        # Return list of pandas df
    return return_tables
