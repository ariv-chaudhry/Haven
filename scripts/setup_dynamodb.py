"""Create Haven's DynamoDB tables."""

from __future__ import annotations

import logging
import sys

from aws.dynamodb.config import (
    load_dynamodb_config,
)
from aws.dynamodb.tables import (
    ensure_tables,
)


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(levelname)s "
            "%(name)s: %(message)s"
        ),
    )

    try:
        config = (
            load_dynamodb_config()
        )

        tables = ensure_tables(
            config
        )

    except Exception as exc:
        print(
            "DynamoDB setup failed: "
            f"{type(exc).__name__}: "
            f"{exc}",
            file=sys.stderr,
        )

        return 1

    print(
        "Haven DynamoDB tables "
        "are ready:"
    )

    print(
        f"  preferences: "
        f"{tables.preferences.name}"
    )

    print(
        f"  activities:  "
        f"{tables.activities.name}"
    )

    print(
        f"  plans:       "
        f"{tables.plans.name}"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())