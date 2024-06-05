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
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from pyvirtualdisplay import Display

# Local Imports
from bank_scrapers import ROOT_DIR
from bank_scrapers.scrapers.common.functions import *
from bank_scrapers.common.functions import convert_to_prometheus, search_files_for_int

# Institution info
INSTITUTION: str = "Fidelity NetBenefits"
SYMBOL: str = "USD"

# Logon page
HOMEPAGE: str = (
    "https://login.fidelity.com/ftgw/Fas/Fidelity/NBPart/Login/Init?ISPBypass=true"
)

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


@screenshot_on_timeout(f"{ROOT_DIR}/errors/{datetime.now()}.png")
def handle_multi_factor_authentication(
    driver: Chrome, wait: WebDriverWait, mfa_auth=None
) -> None:
    """
    Navigates the MFA workflow for this website
    Note that this function only covers Email Me options for now.
    :param driver: The Chrome driver/browser used for this function
    :param wait: The wait object associated with the driver function above
    :param mfa_auth:
    """
    text_me_button: WebElement = wait_and_find_element(
        driver,
        wait,
        (By.XPATH, "//pvd-button[@pvd-id='dom-channel-list-primary-button']"),
    )

    text_me_button.click()

    # Prompt user for OTP code and enter onto the page
    otp_input: WebElement = wait_and_find_element(
        driver, wait, (By.ID, "dom-otp-code-input")
    )
    # Prompt user input for MFA option
    if mfa_auth is None:
        otp_code: str = input("Enter 2FA Code: ")
    else:
        otp_code: str = str(
            search_files_for_int(
                mfa_auth["otp_code_location"],
                "NetBenefits",
                ".txt",
                6,
                10,
                TIMEOUT,
                True,
            )
        )
    otp_input.send_keys(otp_code)

    # Click submit once it becomes clickable
    submit: WebElement = wait_and_find_element(
        driver, wait, (By.ID, "dom-otp-code-submit-button")
    )
    wait.until(EC.element_to_be_clickable((By.ID, "dom-otp-code-submit-button")))
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

    # Enter User
    user: WebElement = wait_and_find_element(
        driver, wait, (By.ID, "dom-username-input")
    )
    user.send_keys(username)

    # Enter Password
    passwd: WebElement = wait_and_find_element(driver, wait, (By.ID, "dom-pswd-input"))
    passwd.send_keys(password)

    # Submit
    submit: WebElement = wait_and_find_element(
        driver, wait, (By.ID, "dom-login-button")
    )
    submit.click()

    # Wait for redirect to landing page or 2FA
    wait.until(
        lambda driver: "https://workplaceservices.fidelity.com/" in driver.current_url
        or str("To verify it's you, we'll send a temporary code to your phone")
        in driver.page_source
    )


@screenshot_on_timeout(f"{ROOT_DIR}/errors/{datetime.now()}.png")
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
    df: pd.DataFrame = df[df["Account Name"].notna()]

    df["Quantity"]: pd.DataFrame = df["Quantity"].fillna(df["Current Value"])
    df["Quantity"]: pd.DataFrame = df["Quantity"].astype(str).str.replace("$", "")

    df["Last Price"]: pd.DataFrame = df["Last Price"].fillna(1)

    df["Symbol"]: pd.DataFrame = df["Symbol"].fillna(df["Description"])
    df["Symbol"]: pd.DataFrame = df["Symbol"].str.replace("FCASH**", "USD")

    return df


@screenshot_on_timeout(f"{ROOT_DIR}/errors/{datetime.now()}.png")
def get_accounts_info(
    username: str, password: str, tmp_dir: str, prometheus: bool = False, mfa_auth=None
) -> List[pd.DataFrame]:
    """
    Gets the accounts info for a given user/pass as a list of pandas dataframes
    :param username: Your username for logging in
    :param password: Your password for logging in
    :param tmp_dir: An empty directory to use for processing the downloaded file
    :param prometheus: True/False value for exporting as Prometheus-friendly exposition
    :param mfa_auth:
    :return: A list of pandas dataframes of accounts info tables
    """
    # Instantiate the virtual display
    display: Display = Display(visible=False, size=(800, 600))
    display.start()

    # Get Driver config
    options: Options = get_chrome_options(CHROME_OPTIONS)

    # Instantiating the Driver
    driver: Chrome = start_chromedriver(options)
    wait: WebDriverWait = WebDriverWait(driver, TIMEOUT)

    enable_downloads(driver, downloads_dir=tmp_dir)

    # Navigate to the logon page and submit credentials
    logon(driver, wait, HOMEPAGE, username, password)

    # If 2FA...
    def is_2fa_redirect():
        if (
            str("To verify it's you, we'll send a temporary code to your phone")
            in driver.page_source
        ):
            return True

    if is_2fa_redirect():
        handle_multi_factor_authentication(driver, wait, mfa_auth)

    # Wait for redirect to landing page
    wait.until(
        lambda driver: "https://workplaceservices.fidelity.com/" in driver.current_url
    )

    # Navigate the site and download the accounts data
    seek_accounts_data(driver, wait)

    file_name: str = os.listdir(tmp_dir)[0]
    try:
        # Process tables
        return_tables: List[pd.DataFrame] = [
            parse_accounts_summary(f"{tmp_dir}/{file_name}")
        ]
        for t in return_tables:
            t["account_type"] = t.apply(
                lambda row: (
                    "deposit" if row["Account Number"].startswith("Z") else "retirement"
                ),
                axis=1,
            )
    except Exception as e:
        print(e)
        sys.exit(1)
    finally:
        # Clean up
        driver.quit()
        os.remove(f"{tmp_dir}/{file_name}")

    # Convert to Prometheus exposition if flag is set
    if prometheus:
        return_tables: List[Tuple[List, float]] = convert_to_prometheus(
            return_tables,
            INSTITUTION,
            "Account Number",
            "Symbol",
            "Quantity",
            "account_type",
        )

    # Return list of pandas df
    return return_tables
