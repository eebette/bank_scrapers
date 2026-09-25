"""
Browser launch helpers shared by the browser-based drivers.

Every driver launches Chrome the same way; this module keeps that call in one
place and adds optional persistent profiles. When the environment variable
``BANK_SCRAPERS_PROFILES_DIR`` is set, each institution gets its own Chrome
user-data directory beneath it, so session cookies, device-trust tokens and
the browser identity survive between runs and a logon only happens when the
previous session has actually expired. Unset, behaviour is unchanged: a
throwaway profile per run.
"""

# Standard Library Imports
import asyncio
import json
import os
import re
import shutil
from typing import Dict, List, Literal, Sequence, Tuple, Union

# Non-standard Library Imports
from patchright.async_api import BrowserContext, Locator, Page, Playwright

# Local Imports
from bank_scrapers.common.log import log

# Root directory for persistent profiles; one sub-directory per institution.
PROFILES_DIR_ENV: str = "BANK_SCRAPERS_PROFILES_DIR"

# Optional comma-separated allow-list of institution slugs (see profile_slug)
# that get a persistent profile. Unset means every institution. Lets a
# deployment enable persistence only for drivers whose post-logon flow copes
# with a remembered device skipping MFA.
PROFILE_BANKS_ENV: str = "BANK_SCRAPERS_PROFILE_BANKS"

# Chrome's process-singleton lock files. Every scheduled run is a fresh
# container with a new hostname and recycled PIDs, so a lock left behind by the
# previous run reads as "profile in use by another computer" and Chrome refuses
# to open the profile. Runs never overlap, so the locks are always stale here.
SINGLETON_FILES: Tuple[str, ...] = (
    "SingletonLock",
    "SingletonSocket",
    "SingletonCookie",
)

# Disk caches, dropped on every launch so a profile does not grow without
# bound. Cookies, local storage and preferences live elsewhere and are kept.
CACHE_DIRS: Tuple[str, ...] = (
    "Default/Cache",
    "Default/Code Cache",
    "Default/GPUCache",
    "Default/DawnGraphiteCache",
    "Default/DawnWebGPUCache",
    "GrShaderCache",
    "GraphiteDawnCache",
    "ShaderCache",
)

# Persistent profiles only: an unclean exit would otherwise leave Chrome's
# "restore pages?" bubble over the page on the next launch.
PERSISTENT_ARGS: List[str] = ["--hide-crash-restore-bubble"]

# Chrome drops non-persistent (session) cookies when it starts, and bank logins
# are session cookies, unless the profile is set to "continue where you left
# off" (session.restore_on_startup == 1). That setting also reopens the last
# run's tabs, which launch_context parks on about:blank.
PREFERENCES_FILE: str = "Default/Preferences"
RESTORE_LAST_SESSION: int = 1

SessionState = Literal["logged_in", "login_form", "unknown"]


def profile_slug(institution: str) -> str:
    """
    Directory name for an institution: lower-case, runs of non-alphanumerics folded to one underscore
    :param institution: The driver's INSTITUTION constant
    :return: A filesystem-safe name
    """
    return re.sub(r"[^a-z0-9]+", "_", institution.lower()).strip("_") or "default"


def profiles_root() -> str:
    """
    The configured profiles root directory
    :return: The directory, or an empty string when persistence is off
    """
    return os.environ.get(PROFILES_DIR_ENV, "").strip()


def is_persistent(institution: str) -> bool:
    """
    Whether this institution's browser profile persists between runs
    :param institution: The driver's INSTITUTION constant
    :return: True when BANK_SCRAPERS_PROFILES_DIR is set and the institution is not excluded by
        BANK_SCRAPERS_PROFILE_BANKS
    """
    if not profiles_root():
        return False
    allowed: str = os.environ.get(PROFILE_BANKS_ENV, "").strip()
    if not allowed:
        return True
    slugs = {profile_slug(name) for name in allowed.split(",") if name.strip()}
    return profile_slug(institution) in slugs


def profile_dir(institution: str) -> str:
    """
    Path of the institution's persistent Chrome profile, prepared for launch: created if missing, locked down to the
    owner, stale singleton locks and disk caches removed. Only call this while no Chrome is running on the profile.
    :param institution: The driver's INSTITUTION constant
    :return: The profile directory, or an empty string (Playwright's "temporary profile") when persistence is off
    """
    root: str = profiles_root()
    if not is_persistent(institution):
        if root:
            log.info(
                f"Persistent profiles not enabled for {institution}; using a throwaway profile"
            )
        return ""

    path: str = os.path.join(root, profile_slug(institution))
    os.makedirs(path, mode=0o700, exist_ok=True)

    # The profile holds live bank sessions: owner-only, root included, whatever the umask or the daemon did.
    for directory in (root, path):
        try:
            os.chmod(directory, 0o700)
        except OSError as exc:
            log.warning(f"Could not restrict permissions on {directory}: {exc}")

    for name in SINGLETON_FILES:
        lock: str = os.path.join(path, name)
        if os.path.lexists(lock):
            log.info(f"Removing stale Chrome lock {name} from {path}")
            os.remove(lock)

    for relative in CACHE_DIRS:
        shutil.rmtree(os.path.join(path, relative), ignore_errors=True)

    _keep_session_cookies(path)

    return path


def _keep_session_cookies(profile_path: str) -> None:
    """
    Sets Chrome's startup preference to "continue where you left off" so session cookies survive a restart. Merges
    into the existing Preferences file, or creates a minimal one on a brand-new profile.
    :param profile_path: The profile directory
    """
    prefs_path: str = os.path.join(profile_path, PREFERENCES_FILE)
    prefs: Dict = {}
    if os.path.exists(prefs_path):
        try:
            with open(prefs_path, "r", encoding="utf-8") as f:
                prefs = json.load(f)
        except (OSError, ValueError) as exc:
            log.warning(f"Could not read {prefs_path}; leaving it alone: {exc}")
            return

    if prefs.get("session", {}).get("restore_on_startup") == RESTORE_LAST_SESSION:
        return

    prefs.setdefault("session", {})["restore_on_startup"] = RESTORE_LAST_SESSION
    os.makedirs(os.path.dirname(prefs_path), exist_ok=True)
    with open(prefs_path, "w", encoding="utf-8") as f:
        json.dump(prefs, f)
    log.info("Set profile to keep session cookies across restarts")


def wipe_profile(institution: str) -> None:
    """
    Deletes the institution's persistent profile so the next launch starts from nothing. No-op when persistence is
    off.
    :param institution: The driver's INSTITUTION constant
    """
    root: str = profiles_root()
    if not is_persistent(institution):
        return

    path: str = os.path.join(root, profile_slug(institution))
    if os.path.isdir(path):
        log.warning(f"Wiping persistent browser profile at {path}")
        shutil.rmtree(path, ignore_errors=True)


async def launch_context(playwright: Playwright, institution: str) -> BrowserContext:
    """
    Launches Chrome exactly as the drivers always have (patchright, headed under the virtual display, no fixed
    viewport): on the institution's persistent profile when BANK_SCRAPERS_PROFILES_DIR is set, on a throwaway
    profile otherwise.
    :param playwright: The playwright object for running this script
    :param institution: The driver's INSTITUTION constant
    :return: The browser context
    """
    user_data_dir: str = profile_dir(institution)
    if user_data_dir:
        log.info(f"Launching browser on persistent profile {user_data_dir}")
        context: BrowserContext = await playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            channel="chrome",
            headless=False,
            no_viewport=True,
            args=PERSISTENT_ARGS,
        )
        # "Continue where you left off" reopens the previous run's tabs; park them so
        # they do not load the bank site behind the driver's own page.
        for restored in list(context.pages):
            if restored.url not in ("", "about:blank"):
                log.info(f"Parking restored tab {restored.url[:80]}")
                try:
                    await restored.goto("about:blank")
                except (
                    Exception
                ) as exc:  # noqa: BLE001 - a dead restored tab is not our problem
                    log.warning(f"Could not park restored tab: {exc}")
        return context

    return await playwright.chromium.launch_persistent_context(
        user_data_dir=str(),
        channel="chrome",
        headless=False,
        no_viewport=True,
    )


async def relaunch_fresh(
    playwright: Playwright, browser: BrowserContext, institution: str
) -> BrowserContext:
    """
    Closes the browser, wipes the institution's persistent profile and launches again from nothing. The floor for
    drivers that reuse sessions: whatever state the old profile was in, the retry is today's fresh-profile run.
    :param playwright: The playwright object for running this script
    :param browser: The context to close
    :param institution: The driver's INSTITUTION constant
    :return: A new browser context on an empty profile
    """
    try:
        await browser.close()
    except Exception as exc:  # noqa: BLE001 - a wedged browser must not mask the retry
        log.warning(f"Ignoring error while closing browser before profile wipe: {exc}")

    wipe_profile(institution)
    return await launch_context(playwright, institution)


async def session_state(
    page: Page,
    landing_url: str,
    logged_in: Sequence[Locator],
    login_form: Sequence[Locator],
    timeout: int,
) -> SessionState:
    """
    Opens the institution's post-logon landing page and reports what is there: something only a signed-in user sees
    ("logged_in"), the logon form ("login_form"), or neither within the timeout ("unknown"). Navigation errors
    propagate; a site that is down is not a reason to touch the profile.
    :param page: The browser application
    :param landing_url: URL a signed-in user can open directly, and that bounces signed-out users to the logon form
    :param logged_in: Locators, any one of which visible means the session is live
    :param login_form: Locators, any one of which visible means the session is gone
    :param timeout: Milliseconds to wait for either group, also used for the navigation
    :return: The session state
    """
    log.info(f"Checking for an existing session at {landing_url}...")
    await page.goto(landing_url, timeout=timeout, wait_until="load")

    tasks: Dict[asyncio.Task, SessionState] = {}
    for state, locators in (("logged_in", logged_in), ("login_form", login_form)):
        for locator in locators:
            task: asyncio.Task = asyncio.create_task(
                locator.filter(visible=True).first.wait_for(
                    state="visible", timeout=timeout
                )
            )
            tasks[task] = state

    try:
        while tasks:
            done, _ = await asyncio.wait(
                tasks.keys(), return_when=asyncio.FIRST_COMPLETED
            )
            for task in done:
                state: SessionState = tasks.pop(task)
                if task.exception() is None:
                    log.info(f"Session check result: {state}")
                    return state
        log.info(
            "Session check result: unknown (neither a signed-in page nor the logon form)"
        )
        return "unknown"
    finally:
        for task in tasks:
            task.cancel()
