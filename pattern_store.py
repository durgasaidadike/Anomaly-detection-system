import json
import os

PATTERN_FILE = "patterns.json"


def save_patterns(data):

    with open(
        PATTERN_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=4
        )


def load_patterns():

    if not os.path.exists(PATTERN_FILE):
        return {}

    try:

        with open(
            PATTERN_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception:

        return {}