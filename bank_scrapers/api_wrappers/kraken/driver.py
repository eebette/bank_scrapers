"""
This file provides the get_accounts_info() function for Kraken (https://www.kraken.com)

Example Usage:
```
info = get_accounts_info(
    "{api_key}",
    "{private_key}",
)
print(info[0].to_string())
```
"""

# Standard library imports
from typing import Dict, List, TypedDict, Tuple, Union
import base64
import hashlib
import hmac
import time
import urllib.parse
import requests

# Non-standard imports
import pandas as pd

# Local Imports
from bank_scrapers.common.log import log
from bank_scrapers.common.functions import convert_to_prometheus, get_usd_rate_crypto
from bank_scrapers.common.types import PrometheusMetric

# Institution info
INSTITUTION: str = "Kraken"

# API Endpoint
API_URL: str = "https://api.kraken.com"

# Alternate TypedDict syntax to create TypedDict with hyphenated keys
Headers: TypedDict = TypedDict("Headers", {"API-Key": str, "API-Sign": str})


def get_kraken_signature(urlpath: str, data: Dict[str, str], secret: str) -> str:
    """
    This function was provided by Kraken to get a valid signature for using an account's
    api key
    :param urlpath: The api endpoint to which to make the call
    :param data: The dict containing the nonce timestamp for forming the api signature
    :param secret: The user's api secret for forming the api signature
    :return: A valid kraken signature
    """
    post_data: str = urllib.parse.urlencode(data)
    encoded: bytes = (str(data["nonce"]) + post_data).encode()
    message: bytes = urlpath.encode() + hashlib.sha256(encoded).digest()

    mac: hmac.HMAC = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
    sig_digest: bytes = base64.b64encode(mac.digest())

    return sig_digest.decode()


def kraken_request(uri_path: str, data, api_key, api_sec) -> requests.Response:
    """
    Attaches auth headers and returns results of a POST request
    :param uri_path: Path of the api call
    :param data: The dict containing the nonce timestamp for forming the api signature
    :param api_key: Your account's api key for this call
    :param api_sec: Your account's secret key for this call
    :return: A requests Response object of the call
    """
    headers: Headers = {
        "API-Key": api_key,
        "API-Sign": get_kraken_signature(uri_path, data, api_sec),
    }
    log.debug(f"Request headers: {headers}")

    log.debug(f"Request URL: {API_URL + uri_path}")
    response: requests.Response = requests.post(
        API_URL + uri_path, headers=headers, data=data
    )
    log.debug(f"Response text: {response.text}")
    return response


def parse_accounts_info(table: Dict, account_id: str) -> pd.DataFrame:
    """
    Takes the requests response json and turns it into a more user-friendly pandas df
    :param table: The json response to parse
    :param account_id: String value to use as the ID for the account
    :return: A pandas df of the response data
    """
    log.debug(f"Response JSON: {table}")
    data: Dict[str, List[str | float]] = {
        "symbol": [s for s in table["result"].keys()],
        "quantity": [q for q in table["result"].values()],
    }
    df: pd.DataFrame = pd.DataFrame(data=data)
    df["account_id"]: pd.DataFrame = account_id
    df["account_type"]: pd.DataFrame = "cryptocurrency"
    df["usd_value"]: pd.DataFrame = df["symbol"].map(get_usd_rate_crypto)
    return df


def get_accounts_info(
    api_key: str, api_sec: str, prometheus: bool = False
) -> Union[List[pd.DataFrame], Tuple[List[PrometheusMetric], List[PrometheusMetric]]]:
    """
    Gets the accounts info for a given set of api keys as a list of pandas dataframes
    :param api_key: Your account's api key for this call
    :param api_sec: Your account's secret key for this call
    :param prometheus: True/False value for exporting as Prometheus-friendly exposition
    :return: A list of pandas dataframes containing the data of the call response
    """
    # Construct the request and print the result
    resp: requests.Response = kraken_request(
        "/0/private/Balance", {"nonce": str(int(1000 * time.time()))}, api_key, api_sec
    )
    table: Dict = resp.json()
    df: pd.DataFrame = parse_accounts_info(table, api_key)
    return_tables: List[pd.DataFrame] = [df]

    # Convert to Prometheus exposition if flag is set
    if prometheus:
        balances: List[PrometheusMetric] = convert_to_prometheus(
            return_tables,
            INSTITUTION,
            "account_id",
            "symbol",
            "quantity",
            "account_type",
        )

        asset_values: List[PrometheusMetric] = convert_to_prometheus(
            return_tables,
            INSTITUTION,
            "account_id",
            "symbol",
            "usd_value",
            "account_type",
        )

        return_tables: Tuple[List[PrometheusMetric], List[PrometheusMetric]] = (
            balances,
            asset_values,
        )

    return return_tables
