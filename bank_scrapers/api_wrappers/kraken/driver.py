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

import base64
import hashlib
import hmac
import time
import urllib.parse
from typing import Dict, List

import pandas as pd
import requests

API_URL: str = "https://api.kraken.com"


def get_kraken_signature(urlpath: str, data, secret):
    """
    This function was provided by Kraken to get a valid signature for using an account's
    api key
    :param urlpath:
    :param data:
    :param secret:
    :return: A valid kraken signature
    """
    postdata = urllib.parse.urlencode(data)
    encoded = (str(data["nonce"]) + postdata).encode()
    message = urlpath.encode() + hashlib.sha256(encoded).digest()

    mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
    sigdigest = base64.b64encode(mac.digest())
    return sigdigest.decode()


# Attaches auth headers and returns results of a POST request
def kraken_request(uri_path: str, data, api_key, api_sec) -> requests.Response:
    """
    Posts a request to Kraken's api
    :param uri_path: Path of the api call
    :param data:
    :param api_key: Your account's api key for this call
    :param api_sec: Your account's secret key for this call
    :return: A requests Response object of the call
    """
    headers: Dict = {
        "API-Key": api_key,
        "API-Sign": get_kraken_signature(uri_path, data, api_sec),
    }
    # get_kraken_signature() as defined in the 'Authentication' section
    req: requests.Response = requests.post(
        (API_URL + uri_path), headers=headers, data=data
    )
    return req


def parse_accounts_info(table: Dict) -> pd.DataFrame:
    """
    Takes the requests response json and turns it into a more user-friendly pandas df
    :param table: The json response to parse
    :return: A pandas df of the response data
    """
    data: Dict[str : List[str], str : List[float]] = {
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
