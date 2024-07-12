"""
Handy functions to be used by any driver
"""

# Standard Imports
import os

# Non-standard Imports
from undetected_playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

# Local Imports
from bank_scrapers.common.log import log


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
