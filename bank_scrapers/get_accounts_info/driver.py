"""Creates a master function for using these functionalities without individual imports"""

from typing import List, Tuple, Union
import pandas as pd

from bank_scrapers.common.types import PrometheusMetric

from bank_scrapers.scrapers.becu.driver import get_accounts_info as get_becu
from bank_scrapers.scrapers.chase.driver import get_accounts_info as get_chase
from bank_scrapers.scrapers.fidelity_netbenefits.driver import (
    get_accounts_info as get_fidelity_nb,
)
from bank_scrapers.scrapers.roundpoint.driver import get_accounts_info as get_roundpoint
from bank_scrapers.scrapers.smbc_prestia.driver import (
    get_accounts_info as get_smbc_prestia,
)
from bank_scrapers.scrapers.uhfcu.driver import get_accounts_info as get_uhfcu
from bank_scrapers.scrapers.vanguard.driver import get_accounts_info as get_vanguard
from bank_scrapers.scrapers.zillow.driver import get_accounts_info as get_zillow

from bank_scrapers.api_wrappers.kraken.driver import get_accounts_info as get_kraken

from bank_scrapers.crypto.bitcoin.driver import get_accounts_info as get_bitcoin
from bank_scrapers.crypto.ethereum.driver import get_accounts_info as get_ethereum

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


async def get_accounts_info(
    driver: str, *args, **kwargs
) -> Union[List[pd.DataFrame], Tuple[List[PrometheusMetric], List[PrometheusMetric]]]:
    if driver not in DRIVERS:
        raise ValueError(f"Must be one of {DRIVERS}.")

    if driver == "kraken":
        return get_kraken(*args, **kwargs)
    elif driver == "bitcoin":
        return await get_bitcoin(*args, **kwargs)
    elif driver == "ethereum":
        return get_ethereum(*args, **kwargs)
    elif driver == "becu":
        return await get_becu(*args, **kwargs)
    elif driver == "chase":
        return await get_chase(*args, **kwargs)
    elif driver == "fidelity_netbenefits":
        return await get_fidelity_nb(*args, **kwargs)
    elif driver == "roundpoint":
        return await get_roundpoint(*args, **kwargs)
    elif driver == "smbc_prestia":
        return await get_smbc_prestia(*args, **kwargs)
    elif driver == "uhfcu":
        return await get_uhfcu(*args, **kwargs)
    elif driver == "vanguard":
        return await get_vanguard(*args, **kwargs)
    elif driver == "zillow":
        return await get_zillow(*args, **kwargs)
