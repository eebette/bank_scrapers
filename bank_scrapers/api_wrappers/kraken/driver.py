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
from typing import Dict, List, TypedDict
import base64
import hashlib
import hmac
import time
import urllib.parse
import requests

# Non-standard imports
import pandas as pd

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

    response: requests.Response = requests.post(
        (API_URL + uri_path), headers=headers, data=data
    )
    return response


def parse_accounts_info(table: Dict) -> pd.DataFrame:
    """
    Takes the requests response json and turns it into a more user-friendly pandas df
    :param table: The json response to parse
    :return: A pandas df of the response data
    """
    data: Dict[str, List[str | float]] = {
        "symbol": [s for s in table["result"].keys()],
        "quantity": [q for q in table["result"].values()],
    }
    df: pd.DataFrame = pd.DataFrame(data=data)
    return df


def get_accounts_info(api_key: str, api_sec: str) -> List[pd.DataFrame]:
    """
    Gets the accounts info for a given set of api keys as a list of pandas dataframes
    :param api_key: Your account's api key for this call
    :param api_sec: Your account's secret key for this call
    :return: A list of pandas dataframes containing the data of the call response
    """
    # Construct the request and print the result
    resp: requests.Response = kraken_request(
        "/0/private/Balance", {"nonce": str(int(1000 * time.time()))}, api_key, api_sec
    )
    table: Dict = resp.json()
    df: pd.DataFrame = parse_accounts_info(table)

    return [df]
