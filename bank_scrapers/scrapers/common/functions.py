"""
Handy functions to be used by any driver
"""

# Standard Imports
import os
import shutil
from pathlib import Path
from typing import Tuple, List, Union

# Non-standard Imports
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.remote.shadowroot import ShadowRoot
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from undetected_chromedriver import ChromeOptions
from selenium_driverless.webdriver import Chrome

from undetected_playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

# Local Imports
from bank_scrapers.common.log import log


def start_chromedriver(options: Options | ChromeOptions) -> Chrome:
    """
    Inspired by https://github.com/ultrafunkamsterdam/undetected-chromedriver/issues/727#issuecomment-1216199477
    A workaround for getting this to run on arm64. Use the locally installed chromedriver as a base if it's there
    :param options: An Options object to use for the driver
    :return: An undetectable chrome instance
    """
    # Check if there's an existing chromedriver
    if os.path.exists("/usr/bin/chromedriver"):
        log.info(f"Detected existing chromedriver folder.")

        filepath: str = os.path.join(
            f"{Path.home()}/.local/share/undetected_chromedriver", "chromedriver_copy"
        )
        if not os.path.exists(f"{Path.home()}/.local/share/undetected_chromedriver"):
            log.info(
                f"Creating directory: {Path.home()}/.local/share/undetected_chromedriver"
            )
            os.makedirs(f"{Path.home()}/.local/share/undetected_chromedriver")

        # If there is, copy it to the undetected chrome installation path
        log.info(f"Copying contents of /usr/bin/chromedriver to: {filepath}")
        shutil.copy("/usr/bin/chromedriver", filepath)

        # Instantiating the Driver with the chromedriver copy
        log.info(f"Running chromedriver with the installation path: {filepath}")
        driver: Chrome = Chrome(options=options, driver_executable_path=filepath)
    else:
        # Otherwise start as normal
        log.info(f"Running chromedriver without any particular installation path...")
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
        log.debug(f"Adding option to chrome options: {arg}")
        chrome_options.add_argument(arg)

    return chrome_options


def enable_downloads(driver: Chrome, downloads_dir: str) -> None:
    """
    Creates a tmp directory and sets chrome experimental options to enable downloads there
    :param driver: The Chrome object for which to enable downloads
    :param downloads_dir: The directory to use to handle downloaded files
    :return: The same chrome options with downloads enabled to tmp dir
    """
    log.info(f"Enabling downloads in chromedriver...")
    params = {"behavior": "allow", "downloadPath": downloads_dir}
    driver.execute_cdp_cmd("Page.setDownloadBehavior", params)


def wait_and_find_elements_in_shadow_root(
    driver: Union[WebDriver, WebElement, Chrome, ShadowRoot],
    wait: WebDriverWait,
    shadow_root_identifier: Tuple[str, str],
    shadow_root_timeout: int,
    identifier: Tuple[str, str],
) -> Tuple[List[WebElement], WebDriverWait]:
    """
    Creates a lightweight wrapper around selenium wait and find_elements with ability to search inside shadow root
    :rtype: object
    :param driver: The Chrome driver/browser used for this function
    :param wait: The wait object associated with the driver function above
    :param shadow_root_identifier: Identifier tuple for the shadow root under which to search for the element identifier
    :param shadow_root_timeout: Timeout (in seconds) to apply to elements inside the shadow root
    :param identifier: The k,v tuple used to identify the web object
    :return: The web element object and the shadow root wait object
    """
    # Navigate shadow root
    log.debug(f"Finding shadow root element: {shadow_root_identifier}")
    shadow_root: ShadowRoot = wait_and_find_element(
        driver, wait, shadow_root_identifier
    ).shadow_root

    # noinspection PyTypeChecker
    # Create new wait under shadow root
    sr_wait: WebDriverWait = WebDriverWait(shadow_root, shadow_root_timeout)

    # Wait until presence of element in shadow root
    log.debug(f"Finding elements inside shadow root: {identifier}")
    sr_wait.until(EC.presence_of_element_located(identifier))

    return shadow_root.find_elements(*identifier), sr_wait


def wait_and_find_element_in_shadow_root(
    driver: Union[WebDriver, WebElement, Chrome, ShadowRoot],
    wait: WebDriverWait,
    shadow_root_identifier: Tuple[str, str],
    shadow_root_timeout: int,
    identifier: Tuple[str, str],
) -> Tuple[WebElement, WebDriverWait]:
    """
    Creates a lightweight wrapper around selenium wait and find_element with ability to search inside shadow root
    :rtype: object
    :param driver: The Chrome driver/browser used for this function
    :param wait: The wait object associated with the driver function above
    :param shadow_root_identifier: Identifier tuple for the shadow root under which to search for the element identifier
    :param shadow_root_timeout: Timeout (in seconds) to apply to elements inside the shadow root
    :param identifier: The k,v tuple used to identify the web object
    :return: The web element object and the shadow root wait object
    """
    # Navigate shadow root
    log.debug(f"Finding shadow root element: {shadow_root_identifier}")
    shadow_root: ShadowRoot = wait_and_find_element(
        driver, wait, shadow_root_identifier
    ).shadow_root

    # noinspection PyTypeChecker
    # Create new wait under shadow root
    sr_wait: WebDriverWait = WebDriverWait(shadow_root, shadow_root_timeout)

    # Wait until presence of element in shadow root
    log.debug(f"Finding element inside shadow root: {identifier}")
    sr_wait.until(EC.presence_of_element_located(identifier))

    return shadow_root.find_element(*identifier), sr_wait


def wait_and_find_element(
    driver: Union[WebDriver, WebElement, Chrome, ShadowRoot],
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
    log.debug(f"Finding element: {identifier}")
    wait.until(EC.presence_of_element_located(identifier))
    return driver.find_element(*identifier)


def wait_and_find_elements(
    driver: Union[WebDriver, WebElement, Chrome, ShadowRoot],
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
    log.debug(f"Finding elements: {identifier}")
    wait.until(EC.presence_of_element_located(identifier))
    return driver.find_elements(*identifier)


def wait_and_find_click_element(
    driver: Union[WebDriver, WebElement, Chrome, ShadowRoot],
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
    log.debug(f"Waiting for element to be clickable: {identifier}")
    wait.until(EC.element_to_be_clickable(identifier))
    return driver.find_element(*identifier)


def screenshot_on_timeout(save_path: str):
    """
    Decorator function for saving a screenshot of the current page if the automation times out
    :param save_path: A path to which to save the screenshot of the webpage on timeout
    """

    def wrapper(func):
        async def _screenshot_on_timeout(*args, **kwargs):
            driver: Page = args[0]
            nonlocal save_path
            try:
                return await func(*args, **kwargs)
            except (PlaywrightTimeoutError, AssertionError):
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                log.warning(f"Saving screenshot to: {save_path}")
                await driver.screenshot(path=save_path)
                raise

        return _screenshot_on_timeout

    return wrapper
