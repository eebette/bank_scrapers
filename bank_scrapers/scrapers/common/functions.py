"""
Handy functions to be used by any driver
"""

# Standard Imports
import os
import shutil
from pathlib import Path
from typing import Tuple, List

# Non-standard Imports
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.remote.shadowroot import ShadowRoot
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import TimeoutException
from undetected_chromedriver import Chrome, ChromeOptions


def start_chromedriver(options: Options | ChromeOptions) -> Chrome:
    """
    Inspired by https://github.com/ultrafunkamsterdam/undetected-chromedriver/issues/727#issuecomment-1216199477
    A workaround for getting this to run on arm64. Use the locally installed chromedriver as a base if it's there
    :param options: An Options object to use for the driver
    :return: An undetectable chrome instance
    """
    # Check if there's an existing chromedriver
    if os.path.exists("/usr/bin/chromedriver"):

        filepath = os.path.join(
            f"{Path.home()}/.local/share/undetected_chromedriver", "chromedriver_copy"
        )
        if not os.path.exists(f"{Path.home()}/.local/share/undetected_chromedriver"):
            os.makedirs(f"{Path.home()}/.local/share/undetected_chromedriver")

        # If there is, copy it to the undetected chrome installation path
        shutil.copy("/usr/bin/chromedriver", filepath)

        # Instantiating the Driver with the chromedriver copy
        driver: Chrome = Chrome(options=options, driver_executable_path=filepath)
    else:
        # Otherwise start as normal
        driver: Chrome = Chrome(options=options)

    return driver


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


def enable_downloads(driver: Chrome, downloads_dir: str) -> None:
    """
    Creates a tmp directory and sets chrome experimental options to enable downloads there
    :param driver: The Chrome object for which to enable downloads
    :param downloads_dir: The directory to use to handle downloaded files
    :return: The same chrome options with downloads enabled to tmp dir
    """
    params = {"behavior": "allow", "downloadPath": downloads_dir}
    driver.execute_cdp_cmd("Page.setDownloadBehavior", params)


def wait_and_find_element(
    driver: WebDriver | WebElement | Chrome | ShadowRoot,
    wait: WebDriverWait,
    identifier: Tuple[str, str],
) -> WebElement:
    """
    Creates a lightweight wrapper around selenium wait and find_element
    :rtype: object
    :param driver: The Chrome driver/browser used for this function
    :param wait: The wait object associated with the driver function above
    :param identifier: The k,v tuple used to identify the web object
    :return: The web element object
    """
    wait.until(EC.presence_of_element_located(identifier))
    return driver.find_element(*identifier)


def wait_and_find_elements(
    driver: WebDriver | WebElement | Chrome | ShadowRoot,
    wait: WebDriverWait,
    identifier: Tuple[str, str],
) -> List[WebElement]:
    """
    Creates a lightweight wrapper around selenium wait and find_elements
    :param driver: The Chrome driver/browser used for this function
    :param wait: The wait object associated with the driver function above
    :param identifier: The k,v tuple used to identify the web object
    :return: The web element object
    """
    wait.until(EC.presence_of_element_located(identifier))
    return driver.find_elements(*identifier)


def wait_and_find_click_element(
    driver: WebDriver | WebElement | Chrome | ShadowRoot,
    wait: WebDriverWait,
    identifier: Tuple[str, str],
) -> WebElement:
    """
    Creates a lightweight wrapper around selenium wait for element to be clickable and find_element
    :param driver: The Chrome driver/browser used for this function
    :param wait: The wait object associated with the driver function above
    :param identifier: The k,v tuple used to identify the web object
    :return: The web element object
    """
    wait.until(EC.element_to_be_clickable(identifier))
    return driver.find_element(*identifier)


def screenshot_on_timeout(save_path: str):
    """
    Decorator function for saving a screenshot of the current page if the automation times out
    :param save_path: A path to which to save the screenshot of the webpage on timeout
    """

    def wrapper(func):
        def _screenshot_on_timeout(*args, **kwargs):
            driver: WebDriver = args[0]
            nonlocal save_path
            try:
                return func(*args, **kwargs)
            except TimeoutException as e:
                print(e)
                driver.save_screenshot(save_path)
                exit(1)

        return _screenshot_on_timeout

    return wrapper
