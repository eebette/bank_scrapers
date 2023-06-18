"""
Handy functions to be used by any driver
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

# Standard Imports
from typing import Tuple, List

# Non-standard Imports
from selenium.common import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.remote.shadowroot import ShadowRoot
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
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
        # If there is, copy it to the undetected chrome installation path
        shutil.copy(
            "/usr/bin/chromedriver",
            f"{Path.home()}/.local/share/undetected_chromedriver/chromedriver_copy",
        )

        # Instantiating the Driver with the chromedriver copy
        driver: Chrome = Chrome(
            options=options,
            driver_executable_path=f"{Path.home()}/.local/share/undetected_chromedriver/chromedriver_copy",
        )
    else:
        # Otherwise start as normal
        driver: Chrome = Chrome(options=options)

    return driver


def wait_and_find_element(
    driver: WebDriver | WebElement | Chrome | ShadowRoot,
    wait: WebDriverWait,
    identifier: Tuple,
) -> WebElement:
    """
    Creates a lightweight wrapper around selenium wait and find_element
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
    identifier: Tuple,
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
    identifier: Tuple,
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


def check_exists(
    driver: WebDriver | WebElement | Chrome | ShadowRoot, identifier: Tuple
) -> bool:
    """
    Returns True if an element exists
    :param driver: The Chrome driver/browser used for this function
    :param identifier: The k,v tuple used to identify the web object
    :return: The web element object
    """
    try:
        driver.find_element(*identifier)
    except NoSuchElementException:
        return False
    return True
