"""Manual live DynamoDB smoke test for Haven."""

from __future__ import annotations

import sys
import uuid

from aws.dynamodb.config import (
    load_dynamodb_config,
)
from aws.dynamodb.repositories import (
    DynamoDBPreferenceStore,
)
from aws.dynamodb.tables import (
    get_tables,
)
from haven.memory.preferences import (
    Preference,
)


def main() -> int:
    household_id = (
        f"haven-smoke-{uuid.uuid4()}"
    )

    key = "smoke_test"

    try:
        config = (
            load_dynamodb_config()
        )

        table = (
            get_tables(config)
            .preferences
        )

        store = (
            DynamoDBPreferenceStore(
                table
            )
        )

        print(
            f"Region: {config.region}"
        )

        print(
            f"Table:  "
            f"{config.preferences_table}"
        )

        expected = Preference(
            household_id=household_id,
            key=key,
            value="HAVEN_DYNAMODB_OK",
        )

        store.save(expected)

        print("write:  OK")

        actual = store.get(
            household_id,
            key,
        )

        if (
            actual is None
            or actual.value
            != expected.value
        ):
            raise RuntimeError(
                "read-back value did not "
                "match the value written"
            )

        print("read:   OK")

        if not store.delete(
            household_id,
            key,
        ):
            raise RuntimeError(
                "temporary smoke-test "
                "item was not deleted"
            )

        print("delete: OK")
        print("HAVEN_DYNAMODB_OK")

        return 0

    except Exception as exc:
        print(
            "DynamoDB smoke test failed: "
            f"{type(exc).__name__}: "
            f"{exc}",
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    sys.exit(main())