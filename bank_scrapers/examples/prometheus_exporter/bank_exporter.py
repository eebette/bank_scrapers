"""
CLI Program for managing a Prometheus Push Gateway exporter using the bank_scrapers library and a locally managed
Bitwarden REST server. On per-bank scrape failure, posts a message and the most recent screenshot to a Matrix room
via a webhook-router endpoint backed by a matrix-webhook bot (e.g. @bank-bot).
"""

# Standard imports
import argparse
import asyncio
import json
import os
import shutil
import subprocess
import time
import traceback
from inspect import signature
from typing import Dict, List, Tuple, Union
from urllib.parse import quote

# Non-standard imports
import requests
from aiohttp import web
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
from patchright.async_api import (
    Error as PlaywrightError,
    TimeoutError as PlaywrightTimeoutError,
)
from web3 import exceptions as web3_exceptions

# Local imports
from bank_scrapers import ROOT_DIR
from bank_scrapers.common.log import log
from bank_scrapers.get_accounts_info import get_accounts_info

SCREENSHOTS_DIR: str = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "bank_exporter", "screenshots"
)


def get_credentials_from_password_manager(
    get_credentials_script: str, bank: Dict
) -> Tuple[str, str]:
    """
    Runs the local shell script provided as a CLI arg to get the credentials from the password manager
    :param get_credentials_script: The string for the shell script to get the credentials
    :param bank: The bank object for which to get the credentials
    :return: The returned object from the shell script
    """
    output: str = subprocess.check_output(
        get_credentials_script.split(" ") + [bank.get("id")]
    ).decode("utf-8")

    return parse_credentials(json.loads(output), bank)


def parse_credentials(
    entry: Dict,
    bank: Dict,
) -> Tuple[str, str]:
    """
    Parses an entry from Bitwarden and returns the username and password for a requested
    entry
    :param entry: The entry for which to get credentials
    :param bank: The bank object for which to get the credentials
    :return: A tuple containing the requested username and password
    """

    # Return normal username key if no custom field name is provided
    if bank.get("username_field_name") is None:
        username: str = entry["login"]["username"]

    # Return element from custom field name if provided
    else:
        username: str = list(
            f["value"]
            for f in entry["fields"]
            if f["name"] == bank.get("username_field_name")
        )[0]

    # Return normal password key if no custom field name is provided
    if bank.get("password_field_name") is None:
        password: str = entry["login"]["password"]

    # Return element from custom field name if provided
    else:
        password: str = list(
            f["value"]
            for f in entry["fields"]
            if f["name"] == bank.get("password_field_name")
        )[0]

    return username, password


# noinspection PyUnresolvedReferences
async def scrape_bank(
    bank: str, bank_scraper_args: Dict, username: str, password: str
) -> Tuple:
    """
    Runs the metrics collector functions and pushes the metrics to the Prometheus Push Gateway
    :param bank: The name of the bank for which to run the collector function
    :param bank_scraper_args: The args to pass to the bank_scrapers function
    :param username: The username for the bank
    :param password: The password for the bank
    :return: A tuple containing the current balances and USD values of assets in the accounts at the bank
    """
    if bank_scraper_args is not None:
        if username is not None and password is not None:
            accounts_info: Tuple = await get_accounts_info(
                bank,
                *(username, password),
                **bank_scraper_args,
                prometheus=True,
            )
        else:
            accounts_info: Tuple = await get_accounts_info(
                bank, **bank_scraper_args, prometheus=True
            )
    else:
        if username is not None and password is not None:
            accounts_info: Tuple = await get_accounts_info(
                bank, *(username, password), prometheus=True
            )
        else:
            accounts_info: Tuple = await get_accounts_info(bank, prometheus=True)

    return accounts_info


# noinspection PyUnresolvedReferences
async def collect_metrics(
    bank: str,
    bank_scraper_args: Dict,
    username: str,
    password: str,
    prometheus_endpoint: str,
    registry: CollectorRegistry,
    current_balances_metrics: Gauge,
    current_values_metrics: Gauge,
) -> None:
    """
    Runs the metrics collector functions and pushes the metrics to the Prometheus Push Gateway
    :param bank: The name of the bank for which to run the collector function
    :param bank_scraper_args: The args to pass to the bank_scrapers function
    :param username: The username for the bank
    :param password: The password for the bank
    :param prometheus_endpoint: The url endpoint for the Prometheus instance
    :param registry: The Prometheus registry object to which to push the metrics
    :param current_balances_metrics: The Prometheus gauge object for current balance
    :param current_values_metrics: The Prometheus gauge object to USD values of the accounts' holdings
    """
    # Get accounts info
    accounts_info: Tuple = await scrape_bank(
        bank, bank_scraper_args, username, password
    )
    current_balances_labels_metrics: List[Tuple[List, float]] = accounts_info[0]
    current_values_labels_metrics: List[Tuple[List, float]] = accounts_info[1]

    # Set metrics for current balances
    for metric in current_balances_labels_metrics:
        labels: List[str] = metric[0]
        value: float = metric[1]
        current_balances_metrics.labels(*labels).set(value)

    # Set metrics for current USD values
    for metric in current_values_labels_metrics:
        labels: List[str] = metric[0]
        value: float = metric[1]
        current_values_metrics.labels(*labels).set(value)

    # Push metrics to push gateway
    push_to_gateway(
        prometheus_endpoint,
        job="bank_exporter",
        registry=registry,
    )


def get_credentials(
    get_credentials_script: str,
    bank: Dict,
) -> Tuple[str, str]:
    """
    Gets credentials for a given bank
    :param get_credentials_script: The string for the shell script to get the credentials
    :param bank: The bank dict object from the config file
    :return: A tuple containing the requested username and password
    """
    print(f"Getting credentials for {bank.get("name").upper()}...")

    # Get credentials using the BitwardenClient interface
    username: Union[str, None]
    password: Union[str, None]
    username, password = get_credentials_from_password_manager(
        get_credentials_script, bank
    )
    return username, password


def get_registry() -> Tuple[CollectorRegistry, Gauge, Gauge]:
    """
    Sets up Prometheus registry and metrics for the bank exporter process
    :return: A tuple containing the registry and gauge objects
    """
    labels: List[str] = [
        "institution",
        "account",
        "account_type",
        "symbol",
    ]
    # Set up Prometheus registry
    registry: CollectorRegistry = CollectorRegistry()

    # Set up the metrics gauges
    current_balances: Gauge = Gauge(
        "current_balance", "Current balance of the asset", labels, registry=registry
    )
    current_values: Gauge = Gauge(
        "current_value", "USD value of 1 unit of the asset", labels, registry=registry
    )

    return registry, current_balances, current_values


def latest_screenshot_for(bank_name: str) -> Union[str, None]:
    """
    Returns the absolute path to the most recent screenshot in the bank_scrapers errors dir, preferring files whose
    name contains the bank name (case-insensitive, spaces normalized to underscores). Returns None if the errors
    dir is missing or empty.
    """
    errors_dir: str = f"{ROOT_DIR}/errors"
    try:
        files: List[str] = sorted(os.listdir(errors_dir), reverse=True)
    except FileNotFoundError:
        return None

    needle: str = bank_name.lower().replace(" ", "_")
    for f in files:
        if not f.lower().endswith(".png"):
            continue
        if needle in f.lower().replace(" ", "_"):
            return os.path.join(errors_dir, f)

    for f in files:
        if f.lower().endswith(".png"):
            return os.path.join(errors_dir, f)
    return None


def post_failure(
    webhook_url: str,
    api_key: str,
    bank_name: str,
    error: BaseException,
    screenshot_url: Union[str, None],
) -> None:
    """
    Posts a Markdown failure message to the webhook-router endpoint. The matrix-webhook fork fetches any http(s)
    image link in the body and emits a captioned m.image event.
    """
    err_msg: str = f"`{type(error).__name__}: {error}`"
    if screenshot_url:
        body: str = (
            f"**Bank scraper FAIL** — `{bank_name}`\n\n"
            f"{err_msg}\n\n"
            f"![screenshot]({screenshot_url})"
        )
    else:
        body: str = (
            f"**Bank scraper FAIL** — `{bank_name}`\n\n"
            f"{err_msg}\n\n"
            f"_(no screenshot captured)_"
        )

    try:
        r: requests.Response = requests.post(
            webhook_url, json={"body": body, "key": api_key}, timeout=60
        )
        r.raise_for_status()
    except Exception as exc:
        print(f"Failed to post failure to {webhook_url}: {exc}")


async def serve_screenshots(port: int) -> web.AppRunner:
    """
    Starts an aiohttp file server that serves SCREENSHOTS_DIR over HTTP on 0.0.0.0:port. Other containers on the
    same docker network can fetch the screenshots; matrix-webhook-bank uses this URL to upload them to Synapse.
    """
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    app: web.Application = web.Application()
    app.router.add_static("/", SCREENSHOTS_DIR, show_index=False)
    runner: web.AppRunner = web.AppRunner(app)
    await runner.setup()
    site: web.TCPSite = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()
    return runner


async def get_bank_metrics(args: argparse.Namespace) -> None:
    """
    CLI function for getting the metrics for all banks in the config file. Pushes successful runs to Prometheus
    Pushgateway. On failure, copies the most recent screenshot to the served screenshots dir and posts the
    failure (with screenshot URL) to the Matrix Alerts channel via the webhook-router.
    """
    # Args
    banks_file: str = args.config_file[0]
    get_credentials_script: str = args.get_credentials_script[0]
    prometheus_endpoint: str = args.prometheus_endpoint[0]
    webhook_url: str = args.webhook_url[0]
    api_key: str = args.api_key[0]
    screenshot_host: str = args.screenshot_host[0]
    screenshot_port: int = int(args.screenshot_port[0])
    banks_arg: List = args.banks

    # Set log level
    log.setLevel("INFO")

    # Set up Prometheus registry and metrics
    registry, current_balances, current_values = get_registry()

    # Get banks data from file
    print(f"Opening banks file at {banks_file}...")
    with open(banks_file) as file:
        banks: Dict = json.load(file)

    # Start the screenshot file server (kept alive for the duration of the run so matrix-webhook-bank can fetch
    # the screenshot synchronously while handling each webhook POST)
    runner: web.AppRunner = await serve_screenshots(screenshot_port)
    print(f"Serving screenshots on 0.0.0.0:{screenshot_port}...")

    try:
        for bank in banks["banks"]:
            bank_name: str = bank["name"]

            if not any([bank_name in banks_arg, "all" in banks_arg]):
                continue

            # Login credentials
            if "ignore_login" not in bank:
                username, password = get_credentials(get_credentials_script, bank)
            else:
                username, password = (None, None)

            # bank_scraper function args
            bank_scraper_args: Union[Dict, None] = bank.get("bank_scraper_args", None)

            # Run bank_scraper function and put into HTTP server
            print(f"Collecting metrics for {bank_name.upper()}...")
            start_time: float = time.time()
            try:
                await collect_metrics(
                    bank_name,
                    bank_scraper_args,
                    username,
                    password,
                    prometheus_endpoint,
                    registry,
                    current_balances,
                    current_values,
                )

            # Scraper crash: copy screenshot, post failure with image link
            except (
                PlaywrightError,
                PlaywrightTimeoutError,
                AssertionError,
                KeyError,
                TimeoutError,
            ) as e:
                print(e)
                print(
                    "Timeout error probably means that the website did something unexpected."
                )
                src: Union[str, None] = latest_screenshot_for(bank_name)
                shot_url: Union[str, None] = None
                if src:
                    filename: str = os.path.basename(src)
                    shutil.copy(src, os.path.join(SCREENSHOTS_DIR, filename))
                    shot_url = (
                        f"http://{screenshot_host}:{screenshot_port}/{quote(filename)}"
                    )
                post_failure(webhook_url, api_key, bank_name, e, shot_url)

            # web3/HTTP error: no useful screenshot, post text only
            except (
                requests.exceptions.HTTPError,
                web3_exceptions.Web3RPCError,
            ) as e:
                print(e)
                print(
                    "Requests error means that the the web3 server didn't return an OK response."
                )
                post_failure(webhook_url, api_key, bank_name, e, None)

            # Print status and proceed loop
            print(f"Completed in {round(time.time() - start_time, 1)} seconds...")
    finally:
        await runner.cleanup()


def main() -> None:
    """
    Entry point into the CLI.
    """
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        "bank-exporter",
        description="Command line interface for pulling accounts info using the bank_scrapers library",
    )

    sub_parser = parser.add_subparsers()
    sub_parser.required = True
    sub_parser.dest = "command"

    # Scrape the metrics
    scrape_parser: argparse.ArgumentParser = sub_parser.add_parser("scrape")
    scrape_parser_required_args = scrape_parser.add_argument_group(
        "required named arguments"
    )
    scrape_parser_required_args.add_argument(
        "--config_file",
        "-c",
        help="The banks.json file containing config for this app",
        nargs=1,
        required=True,
    )
    scrape_parser_required_args.add_argument(
        "--get_credentials_script",
        "-s",
        help="The local shell script which gets the credentials for a bank from the password manager",
        nargs=1,
        required=True,
    )
    scrape_parser_required_args.add_argument(
        "--prometheus_endpoint",
        "-p",
        help="The url endpoint for the Prometheus instance",
        nargs=1,
        required=True,
    )
    scrape_parser_required_args.add_argument(
        "--webhook_url",
        "-w",
        help="The webhook-router URL that fronts the matrix-webhook bot (posts go to the Alerts channel)",
        nargs=1,
        required=True,
    )
    scrape_parser_required_args.add_argument(
        "--api_key",
        "-k",
        help="The shared API key required by the matrix-webhook bot",
        nargs=1,
        required=True,
    )
    scrape_parser_required_args.add_argument(
        "--screenshot_host",
        help=(
            "The hostname matrix-webhook-bank uses to fetch screenshots from this container — typically the "
            "container_name or a network alias on the shared docker network"
        ),
        nargs=1,
        required=True,
    )
    scrape_parser.add_argument(
        "--screenshot_port",
        help="The port the screenshot file server binds to inside the container (default: 8090)",
        nargs=1,
        default=["8090"],
    )
    scrape_parser.add_argument(
        "--banks",
        "-b",
        default="all",
        help="The banks to scrape. Defaults to 'all'",
        nargs="*",
    )
    scrape_parser.set_defaults(func=get_bank_metrics)

    # Parse the args
    args: argparse.Namespace = parser.parse_args()

    log.info("Running with args=%s and log_level=%s", str(args))

    # Try calling the appropriate handler
    try:
        if signature(args.func).parameters:
            asyncio.run(args.func(args))
        else:
            asyncio.run(args.func())
    except Exception:
        print(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
