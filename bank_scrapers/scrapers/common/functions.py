"""
Handy functions to be used by any driver
"""

# Standard Imports
import os

# Local Imports
from bank_scrapers.common.log import log


def _is_pagelike(obj) -> bool:
    """Duck-typed check for a Playwright-compatible Page (works across patchright,
    stock playwright, and camoufox without needing a specific import)."""
    return hasattr(obj, "screenshot") and hasattr(obj, "context")


def screenshot_on_timeout(save_path: str):
    """
    Decorator function for saving a screenshot of the current page if the automation times out
    :param save_path: A path to which to save the screenshot of the webpage on timeout
    """

    def wrapper(func):
        async def _screenshot_on_timeout(*args, **kwargs):
            driver = next((a for a in args if _is_pagelike(a)), None)
            nonlocal save_path
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Intercept Playwright-ish failures (any backend: patchright/playwright/camoufox)
                err_type: str = type(e).__name__
                intercept: bool = (
                    isinstance(e, (AssertionError, KeyError))
                    or "Timeout" in err_type
                    or "Error" in err_type
                )
                if intercept and driver is not None:
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    log.warning(f"Saving screenshot to: {save_path}")
                    try:
                        await driver.screenshot(path=save_path)
                    except Exception as cap_err:
                        log.warning(f"Page screenshot failed: {cap_err}")
                    html_path: str = (
                        save_path.rsplit(".", 1)[0] if "." in os.path.basename(save_path) else save_path
                    ) + ".html"
                    log.warning(f"Saving page HTML to: {html_path}")
                    try:
                        content: str = await driver.content()
                        with open(html_path, "w", encoding="utf-8") as f:
                            f.write(content)
                    except Exception as cap_err:
                        log.warning(f"Page HTML dump failed: {cap_err}")
                raise

        return _screenshot_on_timeout

    return wrapper
