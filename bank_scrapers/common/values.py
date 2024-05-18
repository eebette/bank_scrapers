from enum import Enum
from typing import List


class Labels(Enum):
    LABELS: List[str] = [
        "institution",
        "account",
        "account_type",
        "symbol",
    ]
