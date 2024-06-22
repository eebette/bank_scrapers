from pybadges import badge

from bank_scrapers import version, ROOT_DIR


def create_version_badge(
    left_text: str = "version",
    right_text: str = version(),
    right_color: str = "blue",
    target: str = f"{ROOT_DIR}/docs/badges/version.svg",
) -> None:
    """
    Creates a version badge used in README.md
    :param left_text: The text on the left-hand side of the badge
    :param right_text: The text on the right-hand side of the badge
    :param right_color: The color on the right-hand side of the badge
    :param target: The destination to which to write the svg file output
    """
    b: str = badge(left_text=left_text, right_text=right_text, right_color=right_color)

    with open(target, "w") as f:
        f.write(b)


if __name__ == "__main__":
    create_version_badge()
