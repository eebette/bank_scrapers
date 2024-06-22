import flask
import pybadges
from datetime import datetime
from typing import Dict

app = flask.Flask(__name__)


class BadgeStatus:
    def __init__(self):
        self.status: str = str()
        self.time: str = str()

    def set_status_pass(self):
        self.status = "pass"

    def set_status_fail(self):
        self.status = "fail"

    def set_time(self):
        self.time = datetime.today().strftime("%Y-%m-%d")


BADGES: Dict[str, BadgeStatus] = {
    "becu": BadgeStatus(),
    "chase": BadgeStatus(),
    "fidelity_netbenefits": BadgeStatus(),
    "roundpoint": BadgeStatus(),
    "smbc_prestia": BadgeStatus(),
    "uhfcu": BadgeStatus(),
    "vanguard": BadgeStatus(),
    "zillow": BadgeStatus(),
    "kraken": BadgeStatus(),
    "bitcoin": BadgeStatus(),
    "ethereum": BadgeStatus(),
}


@app.route("/img")
def serve_badge() -> flask.Response:
    """Serve a badge image based on the request query string.
    :return: A flask response object with the requested badge
    """
    b = BADGES[flask.request.args.get("name")]

    badge = pybadges.badge(
        left_text=b.time,
        right_text=f"Test {'Passed' if b.status == 'pass' else 'Failed'}",
        right_color=f"{'green' if b.status == 'pass' else 'red'}",
    )

    response: flask.Response = flask.make_response(badge)
    response.content_type = "image/svg+xml"
    return response


if __name__ == "__main__":
    app.run()
