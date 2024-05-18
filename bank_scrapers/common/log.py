import logging

import sys

sh = logging.StreamHandler(sys.stdout)
# logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
# add the handler
log = logging.getLogger(__name__)
log.addHandler(sh)

logging_levels = vars(logging)["_nameToLevel"]
