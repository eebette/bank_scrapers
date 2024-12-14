"""
CLI Program for managing a Prometheus Push Gateway exporter using the bank_scrapers library and a locally managed
Bitwarden REST server
"""

# Standard imports
import asyncio
from typing import List, Dict, Tuple, Type, Callable, Union
import os
import traceback
import shutil
from inspect import signature
import time
from datetime import datetime
import json
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
import smtplib
import ssl
import argparse

# Non-standard imports
import pandas as pd
import requests
from prometheus_client import Gauge, CollectorRegistry, push_to_gateway
from undetected_playwright.async_api import TimeoutError as PlaywrightTimeoutError
from web3 import exceptions as web3_exceptions

# Local imports
from bank_scrapers.get_accounts_info import get_accounts_info
from bank_scrapers.common.log import log
from bank_scrapers import ROOT_DIR

# Important directories
JAIL_FILE: str = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "bank_exporter", "jail"
)
SCREENSHOTS_DIR: str = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "bank_exporter", "screenshots"
)


class BitwardenClient:
    def __init__(
        self,
        base_url: str = "http://0.0.0.0:8087",
        unlock_api_target: str = "/unlock",
        lock_api_target: str = "/lock",
        sync_api_target: str = "/sync",
        list_api_target: str = "/list/object/items",
        password: str = str(),
    ):
        """
        A client interface for interacting with a local BitWarden HTTP REST server
        :param base_url: The url to which to make HTTP calls
        :param unlock_api_target: The unlock endpoint
        :param lock_api_target: The lock endpoint
        :param sync_api_target: The sync endpoint
        :param list_api_target: The list endpoint
        :param password: The user's password for unlocking the server
        """
        self.base_url: str = base_url
        self.unlock_api_target: str = unlock_api_target
        self.lock_api_target: str = lock_api_target
        self.sync_api_target: str = sync_api_target
        self.list_api_target: str = list_api_target
        self.session_key = str()

        if password == str():
            try:
                self.password = os.environ["BW_PASSWORD"]
            except KeyError as e:
                print(e)
                print(
                    "No password provided. Provide a password when calling this class or by setting the environmental"
                    ' variable "BW_PASSWORD".'
                )
                raise
        else:
            self.password = password

    # noinspection PyMethodParameters
    def check_session_key(func):
        """
        Decorator for checking if a session key is available
        """

        def _check_session_key(self):
            try:
                assert self.session_key
            except AssertionError:
                print(
                    "No session key found. Run the unlock command before accessing vault items."
                )
                raise
            # noinspection PyCallingNonCallable
            return func(self)

        return _check_session_key

    def unlock(self) -> None:
        """
        Unlocks the vault
        """
        response: requests.Response = request_ok(
            function=requests.post,
            url=f"{self.base_url}{self.unlock_api_target}",
            payload={"password": self.password},
        )
        self.session_key = response.json()["data"]["raw"]

    def lock(self) -> None:
        """
        Locks the vault
        """
        request_ok(
            function=requests.post,
            url=f"{self.base_url}{self.lock_api_target}",
            payload={"password": self.password},
        )

    def sync(self) -> None:
        """
        Syncs the vault
        """
        request_ok(
            function=requests.post,
            url=f"{self.base_url}{self.sync_api_target}",
            payload={},
        )

    # noinspection PyArgumentList
    @check_session_key
    def list(self) -> requests.Response:
        """
        Lists all items in the vault
        :return: The requests response from the HTTP call.
        """
        list_response: requests.Response = request_ok(
            function=requests.get,
            url=f"{self.base_url}{self.list_api_target}",
            payload={"session": self.session_key},
        )
        return list_response

    def get_credentials(
        self,
        entry: str,
        username_field_name: str = None,
        password_field_name: str = None,
    ) -> Tuple[str, str]:
        """
        Parses the listed items response and returns credentials for the requested entry
        :param entry: The vault entry for which to get credentials
        :param username_field_name: The name of the custom field containing the username (if the requested username is
        stored outside the standard username field)
        :param password_field_name: The name of the custom field containing the password (if the requested password is
        stored outside the standard password field)
        :return: A tuple containing the requested username and password
        """
        self.sync()
        self.unlock()

        list_response: requests.Response = self.list()

        username: str
        password: str
        username, password = parse_credentials(
            list_response, entry, username_field_name, password_field_name
        )

        self.lock()

        return username, password


def retry(exceptions: Tuple[Type, ...], retries=3, delay=10):
    """
    A decorator function for retrying a function if a given set of exceptions are raised
    :param exceptions: The exceptions for which to retry the function
    :param retries: The amount of times to retry the function
    :param delay: The amount of time (in seconds) to wait before retrying the function
    """

    def wrapper(func):
        def _retry(*args, **kwargs):
            nonlocal retries, delay
            this_retries = retries
            while this_retries > 0:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    print(e)
                    if this_retries == 1:
                        print("All attempts failed.")
                        raise

                    this_retries -= 1
                    print(f"Retrying in {delay} seconds...")
                    time.sleep(delay)

        return _retry

    return wrapper


@retry(exceptions=(AssertionError, requests.exceptions.ConnectionError))
def request_ok(
    function: Callable, url: str, payload: Dict[Union[str, None], Union[str, None]]
) -> requests.Response:
    """
    Simple helper function for running a request and asserting its response is 200 (OK)
    :param function: The requests function to run
    :param url: The request url
    :param payload: The request json
    :return: The OK requests response
    """
    response = function(url=url, json=payload)
    assert response.ok

    return response


def parse_credentials(
    response: requests.Response,
    entry: str,
    username_field_name: str = None,
    password_field_name: str = None,
) -> Tuple[str, str]:
    """
    Parses a requests response containing BitWarden vault items and returns the username and password for a requested
    entry
    :param response: The requests response to parse
    :param entry: The entry for which to get credentials
    :param username_field_name: The name of the custom field containing the username (if the requested username is
    stored outside the standard username field)
    :param password_field_name: The name of the custom field containing the password (if the requested password is
    stored outside the standard password field)
    :return: A tuple containing the requested username and password
    """
    username: str = str()
    password: str = str()

    # Iterate the items in the response
    for item in response.json()["data"]["data"]:

        # Match the entry name and the item in the response
        if item["name"].lower() == entry.lower():

            # Return normal username key if no custom field name is provided
            if username_field_name is None:
                username: str = item["login"]["username"]

            # Return element from custom field name if provided
            else:
                username: str = list(
                    f["value"]
                    for f in item["fields"]
                    if f["name"] == username_field_name
                )[0]

            # Return normal password key if no custom field name is provided
            if password_field_name is None:
                password: str = item["login"]["password"]

            # Return element from custom field name if provided
            else:
                password: str = list(
                    f["value"]
                    for f in item["fields"]
                    if f["name"] == password_field_name
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
    push_to_gateway("0.0.0.0:9091", job="bank_exporter", registry=registry)


def update_test_status(file_location: str, bank_name: str, passed: bool) -> None:
    """
    Updates the test status of a scrape in a given JSON file
    :param file_location: The file location for the JSON file containing the test data
    :param bank_name: The name of the bank for which to update the test
    :param passed: boolean value for if the test is passed (True) or failed (False)
    """
    # Create the JSON file if it doesn't exist
    if not os.path.exists(file_location):
        os.mknod(file_location)

    # Instantiate the tests dict as empty if the file is empty, otherwise load the file JSON
    if os.stat(file_location).st_size == 0:
        tests_dict: Dict = dict()
    else:
        with open(file_location, "r") as tests:
            tests_dict: Dict = json.load(tests)

    # Set the most recent test date and passed/failed status
    tests_dict[bank_name] = {
        "test_date": datetime.today().strftime("%Y-%m-%d"),
        "status": "passed" if passed else "failed",
    }

    # Write the JSON back to the file
    with open(file_location, "wt") as tests:
        json.dump(tests_dict, tests)


def get_credentials(bank: Dict, bank_name: str) -> Tuple[str, str]:
    """
    Gets credentials for a given bank
    :param bank: The bank dict object from the config file
    :param bank_name: The name of the bank for which to get credentials
    :return: A tuple containing the requested username and password
    """
    print(f"Getting credentials for {bank_name.upper()}...")

    # Get the custom username/password field names if exists in the config
    username_field_name: Union[str, None] = bank.get("username_field_name", None)
    password_field_name: Union[str, None] = bank.get("password_field_name", None)

    # Get credentials using the BitwardenClient interface
    username: Union[str, None]
    password: Union[str, None]
    username, password = BitwardenClient().get_credentials(
        bank_name, username_field_name, password_field_name
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


async def get_bank_metrics(args: argparse.Namespace) -> None:
    """
    CLI function for getting the metrics for all banks in the config file and update tests and jail. On timeout, will
    move a scraper into the jail file and move the generated screenshot to a local folder
    :param args: The argparse args
    """
    # Args
    banks_file: str = args.config_file[0]
    tests_file: str = args.tests_file[0]
    banks_arg: List = args.banks

    # Set log level
    log.setLevel("INFO")

    # Set up Prometheus registry and metrics
    registry, current_balances, current_values = get_registry()

    # Get banks data from file
    print(f"Opening banks file at {banks_file}...")
    with open(banks_file) as file:
        banks: Dict = json.load(file)

    try:
        with open(JAIL_FILE, "w+") as file:
            jail: List = list(line.rstrip() for line in file)
    except FileNotFoundError:
        jail: List = list()

    # Loop through banks file
    for bank in banks["banks"]:

        # Banks name
        bank_name: str = bank["name"]
        if bank_name in jail:
            print(
                f"{bank_name} was found in the jail file. Re-enable if you wish to scrape this bank."
            )

        elif any([bank_name in banks_arg, "all" in banks_arg]):
            # Login credentials
            if "ignore_login" not in bank:
                username, password = get_credentials(bank, bank_name)
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
                    registry,
                    current_balances,
                    current_values,
                )

                # Update the test badge
                update_test_status(tests_file, bank_name, True)

            # On timeout error....
            except (PlaywrightTimeoutError, AssertionError) as e:
                print(e)
                print(
                    "Timeout error probably means that the website did something unexpected."
                )

                # Update the jail file
                with open(JAIL_FILE, "a") as file:
                    file.write(f"{bank_name}\n")

                # Update the test badge
                update_test_status(tests_file, bank_name, False)

                # Copy the most recent screenshot to the mounted directory
                screenshot_file: str = sorted(
                    os.listdir(f"{ROOT_DIR}/errors"), reverse=True
                )[0]
                shutil.copy(
                    f"{ROOT_DIR}/errors/{screenshot_file}",
                    SCREENSHOTS_DIR,
                )

            # On requests error....
            except (requests.exceptions.HTTPError, web3_exceptions.Web3RPCError) as e:
                print(e)
                print(
                    "Requests error means that the the web3 server didn't return an OK response."
                )

                # Update the test badge
                update_test_status(tests_file, bank_name, False)

            # Print status and proceed loop
            print(f"Completed in {round(time.time() - start_time, 1)} seconds...")


async def send_report(args: argparse.Namespace) -> None:
    """
    CLI function for sending a report based on the current test and jail status each scraper. Tries to find and attach
    the most recent screenshot for each scraper in failed/jail status
    :param args: The argparse args
    """
    # Args
    address: str = args.address[0]
    port: int = args.port[0]
    username: str = args.username[0]
    password: str = args.password[0]
    from_address: str = args.from_address[0]
    to_address: str = args.to_address[0]
    tests_file: str = args.tests_file[0]

    # Create an SSL context
    context: ssl.SSLContext = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    # Initiate the message
    msg: MIMEMultipart = MIMEMultipart()
    msg["Subject"] = "Scrapers Report"
    msg["From"] = from_address

    # Open the tests file
    with open(tests_file, "r") as tests:
        tests_dict: Dict = json.load(tests)

    # Filter for user args
    if args.include[0] == "success":
        tests_dict: Dict = dict(
            kv for kv in tests_dict.items() if kv[1]["status"] == "passed"
        )
    elif args.include[0] == "fail":
        tests_dict: Dict = dict(
            kv for kv in tests_dict.items() if kv[1]["status"] == "failed"
        )

    # If there are any items or if user specifies to send empty report
    if len(list(tests_dict.items())) > 0 or args.if_none[0] == "send_empty":

        # Turn tests dict into HTML
        tests_html: str = pd.DataFrame(data=tests_dict).T.to_html()

        # Center-align the cells
        tests_html: str = tests_html.replace("<tr>", '<tr align="center">')

        # Style
        tests_html: str = tests_html.replace("passed", "✅")
        tests_html: str = tests_html.replace("failed", "⛔")

        # Format the text and attach it to the message
        tests_part: MIMEText = MIMEText(tests_html, "html")
        msg.attach(tests_part)

        # Prepare the erred/jailed scraped if user doesn't specify success only
        if args.include[0] != "success":

            # Get the jail list
            try:
                with open(JAIL_FILE, "r") as file:
                    jail: List = list(line.rstrip().lower() for line in file)
            except FileNotFoundError:
                jail: List = list()

            # Turn the jail list into HTML
            jail_html: str = pd.DataFrame(
                data=jail, columns=["Disabled Scrapers"]
            ).to_html(index=False)

            # Format the text and attach it to the message
            jail_part: MIMEText = MIMEText(jail_html, "html")
            msg.attach(jail_part)

            # Get the list of erred tests
            errors: List[str] = list(
                k[0] for k in tests_dict.items() if k[1]["status"] == "failed"
            )

            # Find the most recent screenshot (if exists) for these tests and attach to message
            for scraper in set(jail + errors):
                for file in sorted(os.listdir(SCREENSHOTS_DIR), reverse=True):
                    filename: str = os.fsdecode(file)
                    if (
                        filename.endswith(".png")
                        and scraper.lower() in filename.replace(" ", "_").lower()
                    ):
                        full_filepath: str = os.path.join(SCREENSHOTS_DIR, filename)

                        with open(full_filepath, "rb") as f:
                            part = MIMEImage(f.read())

                        print(f"Attaching {filename}")
                        msg.attach(part)

                        # Only attach most recent
                        break

        # Instantiate server and send the message
        with smtplib.SMTP(address, port) as server:
            server.starttls(context=context)
            server.login(username, password)
            server.sendmail(from_address, to_address, msg.as_string())


async def enable(args: argparse.Namespace) -> None:
    """
    CLI function for removing scrapers from the jail file
    :param args: The argparse args
    """
    # Truncate the file if user indicates 'all'
    if "all" in args.scrapers:
        open(JAIL_FILE, "w+").close()
        print("All scrapes enabled.")

    # Otherwise
    else:
        # Create a list from the jail file
        with open(JAIL_FILE, "r") as file:
            jail: List = list(line.rstrip().lower() for line in file)

        # Remove the provided scrapers
        for scraper in args.scrapers:
            try:
                jail.remove(scraper.lower())
                print(f"{scraper.upper()} enabled.")
            except ValueError:
                print(f"{scraper.upper()} isn't disabled.")

        # Rewrite the jail file
        with open(JAIL_FILE, "w+") as file:
            file.write("\n".join(jail))


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
        "--tests_file",
        "-t",
        help="The tests.json file to document the run results",
        nargs=1,
        required=True,
    )
    scrape_parser.add_argument(
        "--banks",
        "-b",
        default="all",
        help="The banks to scrape. Defaults to 'all'",
        nargs="*",
    )
    scrape_parser.set_defaults(func=get_bank_metrics)

    # Generate at send a report
    report_parser: argparse.ArgumentParser = sub_parser.add_parser("report")
    report_parser_required_args = report_parser.add_argument_group(
        "required named arguments"
    )
    report_parser_required_args.add_argument(
        "--address",
        "-a",
        help="The web address of the SMTP server to send the email",
        nargs=1,
        required=True,
    )
    report_parser_required_args.add_argument(
        "--port",
        "-p",
        help="The port on the web address for the SMTP server",
        nargs=1,
        required=True,
    )
    report_parser_required_args.add_argument(
        "--username",
        "-u",
        help="The login username to use for authenticating with the SMTP server",
        nargs=1,
        required=True,
    )
    report_parser_required_args.add_argument(
        "--password",
        "-pp",
        help="The password to use for authenticating with the SMTP server",
        nargs=1,
        required=True,
    )
    report_parser_required_args.add_argument(
        "--from_address",
        "-f",
        help="The address from which to send the report email",
        nargs=1,
        required=True,
    )
    report_parser_required_args.add_argument(
        "--to_address",
        "-t",
        help="The address to which to send the report email",
        nargs=1,
        required=True,
    )
    report_parser_required_args.add_argument(
        "--tests_file",
        "-tf",
        help="The tests.json file to document the run results",
        nargs=1,
        required=True,
    )
    report_parser.add_argument(
        "--include",
        "-i",
        default="all",
        choices={"all", "fail", "success"},
        help="Select which run statuses to include in the report ('all', 'fail', success')",
        nargs=1,
    )
    report_parser.add_argument(
        "--if_none",
        "-n",
        default="stop_send",
        choices={"send_empty", "stop_send"},
        help="Select what to do if there are no runs in the selecting inclusion",
        nargs=1,
    )
    report_parser.set_defaults(func=send_report)

    # Enable a bank scraper if it's disabled
    enable_parser: argparse.ArgumentParser = sub_parser.add_parser("enable")
    enable_parser.add_argument(
        "--scrapers",
        "-s",
        default="all",
        help="Clear the status and re-enable a bank to be scraped",
        nargs="*",
    )
    enable_parser.set_defaults(func=enable)

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
