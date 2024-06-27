import logging
import sys
from typing import Dict

logging_levels: Dict[str, int] = vars(logging)["_nameToLevel"]

stream_handler: logging.StreamHandler = logging.StreamHandler(sys.stdout)

log: logging.Logger = logging.getLogger(__name__)
log.addHandler(stream_handler)

log.debug(f"Logger initialized.")
