"""
Regenerates the version badge referenced by README.md.

Run from the repository root so the checked-out package (not an installed copy)
supplies the version number:

    python -m bank_scrapers.docs.scripts.version_badge
"""

from pathlib import Path

from anybadge import Badge

from bank_scrapers import version

BADGE_PATH: Path = Path(__file__).resolve().parents[1] / "badges" / "version.svg"


def create_version_badge(
    left_text: str = "version",
    right_text: str = version(),
    right_color: str = "#007ec6",
    target: str = str(BADGE_PATH),
) -> None:
    """
    Creates a version badge used in README.md
    :param left_text: The text on the left-hand side of the badge
    :param right_text: The text on the right-hand side of the badge
    :param right_color: The color on the right-hand side of the badge
    :param target: The destination to which to write the svg file output
    """
    Badge(label=left_text, value=right_text, default_color=right_color).write_badge(
        target, overwrite=True
    )


if __name__ == "__main__":
    create_version_badge()
