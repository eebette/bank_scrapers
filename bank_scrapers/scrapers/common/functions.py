"""
Handy functions to be used by any driver
"""

# Standard Imports
import os
from random import randint, uniform

# Local Imports
from bank_scrapers.common.log import log


def _is_pagelike(obj) -> bool:
    """Duck-typed check for a Playwright-compatible Page (works across patchright,
    stock playwright, and camoufox without needing a specific import)."""
    return hasattr(obj, "screenshot") and hasattr(obj, "context")


async def settle_after_navigation(
    page, label: str, min_ms: int = 12000, max_ms: int = 18000
) -> None:
    """
    Wait a randomized window for bot-scoring init bursts (Akamai sensor JS,
    ThreatMetrix/Tarsus collectors, PingOne DaVinci behavioral fingerprinting)
    to clear after a navigation. networkidle is misleading on these sites
    because the collectors enter steady-state polling that never stops on
    their own; acting before the burst settles is itself a bot signal.
    """
    delay_ms: int = randint(min_ms, max_ms)
    log.info(f"[settle/{label}] sleeping {delay_ms}ms for init burst to clear")
    await page.wait_for_timeout(delay_ms)


async def human_move_to(page, locator) -> None:
    """
    Move the mouse along a curved two-segment path into the locator's bounding
    box, generating mousemove events bot-scoring JS can score as human. The
    waypoint overshoot defeats linear-path heuristics.
    """
    box = await locator.bounding_box()
    if box is None:
        return
    tx: float = box["x"] + box["width"] * uniform(0.3, 0.7)
    ty: float = box["y"] + box["height"] * uniform(0.3, 0.7)
    wx: float = tx + uniform(-80, 80)
    wy: float = ty + uniform(-80, 80)
    await page.mouse.move(wx, wy, steps=randint(15, 30))
    await page.wait_for_timeout(randint(40, 140))
    await page.mouse.move(tx, ty, steps=randint(10, 20))
    await page.wait_for_timeout(randint(60, 200))


async def warm_up_session(page) -> None:
    """
    Generate idle mouse and scroll activity so bot-scoring JS has a stream of
    real-looking input events to score before any form interaction begins.
    """
    for _ in range(randint(2, 4)):
        await page.mouse.move(
            uniform(100, 1100), uniform(100, 600), steps=randint(10, 25)
        )
        await page.wait_for_timeout(randint(200, 600))
    await page.mouse.wheel(0, randint(80, 250))
    await page.wait_for_timeout(randint(300, 700))
    await page.mouse.wheel(0, -randint(40, 200))
    await page.wait_for_timeout(randint(200, 500))


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
