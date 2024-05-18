from enum import Enum


class ExpositionFormats(Enum):
    PROMETHEUS = "total_assets{{institution=\"{0}\", account=\"{1}\", account_type=\"{2}\", symbol=\"{3}\"}} {4}"
