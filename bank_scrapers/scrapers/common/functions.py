"""
Handy functions to be used by any driver
"""

# Standard Imports
import os

# Non-standard Imports
from patchright.async_api import Page, TimeoutError as PlaywrightTimeoutError

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
            except (PlaywrightTimeoutError, AssertionError, KeyError):
                os.makedirs(os.path.dirname(save_path), exist_ok=True)

                log.warning(f"Saving screenshot to: {save_path}")
                await driver.screenshot(path=save_path)

                client = await driver.context.new_cdp_session(driver)
                mhtml_coroutine = await client.send("Page.captureSnapshot")
                mhtml = mhtml_coroutine["data"]

                with open(
                    save_path.replace(".png", ".html"), "w+", encoding="utf-8"
                ) as f:
                    f.write(mhtml)

                raise

        return _screenshot_on_timeout

    return wrapper
