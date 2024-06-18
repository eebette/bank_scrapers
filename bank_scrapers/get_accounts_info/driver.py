"""Creates a master function for using these functionalities without individual imports"""

from typing import List, Tuple, Union
import pandas as pd

from bank_scrapers.common.types import PrometheusMetric

from bank_scrapers.api_wrappers import kraken
from bank_scrapers.crypto import bitcoin, ethereum
from bank_scrapers.scrapers import (
    becu,
    chase,
    fidelity_netbenefits,
    roundpoint,
    smbc_prestia,
    uhfcu,
    vanguard,
    zillow,
)

DRIVERS: set[str] = {
    "kraken",
    "bitcoin",
    "ethereum",
    "becu",
    "chase",
    "fidelity_netbenefits",
    "roundpoint",
    "smbc_prestia",
    "uhfcu",
    "vanguard",
    "zillow",
}


def get_accounts_info(
    driver: str, *args
) -> Union[List[pd.DataFrame], Tuple[List[PrometheusMetric], List[PrometheusMetric]]]:
    if driver not in DRIVERS:
        raise ValueError(f"results: status must be one of {DRIVERS}.")

    if driver == "kraken":
        return kraken.get_accounts_info(*args)
    elif driver == "bitcoin":
        return bitcoin.get_accounts_info(*args)
    elif driver == "ethereum":
        return ethereum.get_accounts_info(*args)
    elif driver == "becu":
        return becu.get_accounts_info(*args)
    elif driver == "chase":
        return chase.get_accounts_info(*args)
    elif driver == "fidelity_netbenefits":
        return fidelity_netbenefits.get_accounts_info(*args)
    elif driver == "roundpoint":
        return roundpoint.get_accounts_info(*args)
    elif driver == "smbc_prestia":
        return smbc_prestia.get_accounts_info(*args)
    elif driver == "uhfcu":
        return uhfcu.get_accounts_info(*args)
    elif driver == "vanguard":
        return vanguard.get_accounts_info(*args)
    elif driver == "zillow":
        return zillow.get_accounts_info(*args)
