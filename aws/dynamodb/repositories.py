"""DynamoDB-backed Haven persistence adapters."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from boto3.dynamodb.conditions import Key

from aws.dynamodb.client import create_dynamodb_resource
from aws.dynamodb.config import (
    DynamoDBConfig,
    load_dynamodb_config,
)

from haven.memory.activity import (
    ActivityRecord,
    ActivityStore,
    ActivityType,
)
from haven.memory.preferences import (
    Preference,
    PreferenceStore,
)
from haven.models.plan import Plan


_HOUSEHOLD_SCOPE = "HOUSEHOLD"
_PERSON_SCOPE = "PERSON"


class DynamoDBPreferenceStore(PreferenceStore):
    """DynamoDB implementation of Haven's preference store."""

    def __init__(
        self,
        table: Any,
    ) -> None:
        self._table = table

    def save(
        self,
        preference: Preference,
    ) -> Preference:
        self._table.put_item(
            Item=_preference_to_item(preference)
        )

        return preference

    def get(
        self,
        household_id: str,
        key: str,
        person_id: str | None = None,
    ) -> Preference | None:
        household_id = _require_text(
            household_id,
            "household_id",
        )

        key = _require_text(
            key,
            "key",
        )

        response = self._table.get_item(
            Key={
                "household_id": household_id,
                "preference_id": _preference_id(
                    key,
                    person_id,
                ),
            },
            ConsistentRead=True,
        )

        item = response.get("Item")

        if not item:
            return None

        return _preference_from_item(item)

    def list(
        self,
        household_id: str,
        person_id: str | None = None,
    ) -> list[Preference]:
        household_id = _require_text(
            household_id,
            "household_id",
        )

        prefix = _preference_prefix(person_id)

        items = _query_all(
            self._table,
            KeyConditionExpression=(
                Key("household_id").eq(household_id)
                & Key("preference_id").begins_with(prefix)
            ),
            ConsistentRead=True,
        )

        preferences = [
            _preference_from_item(item)
            for item in items
        ]

        return sorted(
            preferences,
            key=lambda preference: preference.key,
        )

    def delete(
        self,
        household_id: str,
        key: str,
        person_id: str | None = None,
    ) -> bool:
        household_id = _require_text(
            household_id,
            "household_id",
        )

        key = _require_text(
            key,
            "key",
        )

        response = self._table.delete_item(
            Key={
                "household_id": household_id,
                "preference_id": _preference_id(
                    key,
                    person_id,
                ),
            },
            ReturnValues="ALL_OLD",
        )

        return bool(
            response.get("Attributes")
        )


class DynamoDBActivityStore(ActivityStore):
    """DynamoDB implementation of Haven's activity history."""

    def __init__(
        self,
        table: Any,
    ) -> None:
        self._table = table

    def record(
        self,
        activity: ActivityRecord,
    ) -> ActivityRecord:
        self._table.put_item(
            Item=_activity_to_item(activity)
        )

        return activity

    def list(
        self,
        household_id: str,
        *,
        activity_type: ActivityType | None = None,
        limit: int | None = None,
    ) -> list[ActivityRecord]:
        household_id = _require_text(
            household_id,
            "household_id",
        )

        if limit is not None and limit < 0:
            raise ValueError(
                "limit must not be negative"
            )

        if limit == 0:
            return []

        records: list[ActivityRecord] = []

        exclusive_start_key: (
            dict[str, Any] | None
        ) = None

        while True:
            kwargs: dict[str, Any] = {
                "KeyConditionExpression": (
                    Key("household_id").eq(
                        household_id
                    )
                ),
                "ScanIndexForward": False,
                "ConsistentRead": True,
            }

            if exclusive_start_key:
                kwargs[
                    "ExclusiveStartKey"
                ] = exclusive_start_key

            if (
                limit is not None
                and activity_type is None
            ):
                kwargs["Limit"] = max(
                    1,
                    limit - len(records),
                )

            response = self._table.query(
                **kwargs
            )

            for item in response.get(
                "Items",
                [],
            ):
                record = _activity_from_item(
                    item
                )

                if (
                    activity_type is None
                    or record.activity_type
                    == activity_type
                ):
                    records.append(record)

                    if (
                        limit is not None
                        and len(records) >= limit
                    ):
                        return records

            exclusive_start_key = (
                response.get(
                    "LastEvaluatedKey"
                )
            )

            if not exclusive_start_key:
                break

        return records


class DynamoDBPlanRepository:
    """Persistence adapter for Haven Plan objects."""

    def __init__(
        self,
        table: Any,
    ) -> None:
        self._table = table

    def save_plan(
        self,
        plan: Plan,
        household_id: str,
    ) -> Plan:
        household_id = _require_text(
            household_id,
            "household_id",
        )

        self._table.put_item(
            Item={
                "plan_id": plan.id,
                "household_id": household_id,
                "created_at": _utc_iso(
                    plan.created_at
                ),
                "payload": (
                    plan.model_dump_json()
                ),
            }
        )

        return plan

    def get_plan(
        self,
        plan_id: str,
    ) -> Plan | None:
        plan_id = _require_text(
            plan_id,
            "plan_id",
        )

        response = self._table.get_item(
            Key={
                "plan_id": plan_id
            },
            ConsistentRead=True,
        )

        item = response.get("Item")

        if not item:
            return None

        return Plan.model_validate_json(
            item["payload"]
        )

    def delete_plan(
        self,
        plan_id: str,
    ) -> bool:
        plan_id = _require_text(
            plan_id,
            "plan_id",
        )

        response = self._table.delete_item(
            Key={
                "plan_id": plan_id
            },
            ReturnValues="ALL_OLD",
        )

        return bool(
            response.get("Attributes")
        )


class DynamoDBRepositories:
    """Bundle containing Haven's DynamoDB repositories."""

    def __init__(
        self,
        preferences: DynamoDBPreferenceStore,
        activity: DynamoDBActivityStore,
        plans: DynamoDBPlanRepository,
    ) -> None:
        self.preferences = preferences
        self.activity = activity
        self.plans = plans


def create_dynamodb_repositories(
    config: DynamoDBConfig | None = None,
    *,
    dynamodb: Any | None = None,
) -> DynamoDBRepositories:
    """Construct repository adapters without creating tables."""

    resolved = (
        config
        or load_dynamodb_config()
    )

    resource = (
        dynamodb
        or create_dynamodb_resource(
            resolved
        )
    )

    return DynamoDBRepositories(
        preferences=DynamoDBPreferenceStore(
            resource.Table(
                resolved.preferences_table
            )
        ),
        activity=DynamoDBActivityStore(
            resource.Table(
                resolved.activities_table
            )
        ),
        plans=DynamoDBPlanRepository(
            resource.Table(
                resolved.plans_table
            )
        ),
    )


def _preference_id(
    key: str,
    person_id: str | None,
) -> str:
    key = _require_text(
        key,
        "key",
    )

    if person_id is None:
        return (
            f"{_HOUSEHOLD_SCOPE}#{key}"
        )

    return (
        f"{_PERSON_SCOPE}#"
        f"{_require_text(person_id, 'person_id')}#"
        f"{key}"
    )


def _preference_prefix(
    person_id: str | None,
) -> str:
    if person_id is None:
        return f"{_HOUSEHOLD_SCOPE}#"

    return (
        f"{_PERSON_SCOPE}#"
        f"{_require_text(person_id, 'person_id')}#"
    )


def _preference_to_item(
    preference: Preference,
) -> dict[str, Any]:
    return {
        "household_id": (
            preference.household_id
        ),
        "preference_id": (
            _preference_id(
                preference.key,
                preference.person_id,
            )
        ),
        "key": preference.key,
        "person_id": (
            preference.person_id or ""
        ),
        "value_json": json.dumps(
            preference.value,
            separators=(",", ":"),
            ensure_ascii=False,
        ),
        "updated_at": _utc_iso(
            preference.updated_at
        ),
    }


def _preference_from_item(
    item: dict[str, Any],
) -> Preference:
    person_id = (
        item.get("person_id")
        or None
    )

    return Preference.model_validate(
        {
            "household_id": (
                item["household_id"]
            ),
            "key": item["key"],
            "value": json.loads(
                item["value_json"]
            ),
            "person_id": person_id,
            "updated_at": (
                item["updated_at"]
            ),
        }
    )


def _activity_to_item(
    activity: ActivityRecord,
) -> dict[str, Any]:
    occurred_at = _utc_iso(
        activity.occurred_at
    )

    return {
        "household_id": (
            activity.household_id
        ),
        "activity_key": (
            f"{occurred_at}#{activity.id}"
        ),
        "activity_id": activity.id,
        "activity_type": (
            activity.activity_type.value
        ),
        "summary": activity.summary,
        "details_json": json.dumps(
            activity.details,
            separators=(",", ":"),
            ensure_ascii=False,
        ),
        "occurred_at": occurred_at,
    }


def _activity_from_item(
    item: dict[str, Any],
) -> ActivityRecord:
    return ActivityRecord.model_validate(
        {
            "id": item["activity_id"],
            "household_id": (
                item["household_id"]
            ),
            "activity_type": (
                item["activity_type"]
            ),
            "summary": item["summary"],
            "details": json.loads(
                item.get(
                    "details_json",
                    "{}",
                )
            ),
            "occurred_at": (
                item["occurred_at"]
            ),
        }
    )


def _query_all(
    table: Any,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    exclusive_start_key: (
        dict[str, Any] | None
    ) = None

    while True:
        page_kwargs = dict(kwargs)

        if exclusive_start_key:
            page_kwargs[
                "ExclusiveStartKey"
            ] = exclusive_start_key

        response = table.query(
            **page_kwargs
        )

        items.extend(
            response.get(
                "Items",
                [],
            )
        )

        exclusive_start_key = (
            response.get(
                "LastEvaluatedKey"
            )
        )

        if not exclusive_start_key:
            return items


def _utc_iso(
    value: datetime,
) -> str:
    if value.tzinfo is None:
        raise ValueError(
            "datetime values stored in DynamoDB "
            "must be timezone-aware"
        )

    return (
        value.astimezone(UTC)
        .isoformat(
            timespec="microseconds"
        )
        .replace("+00:00", "Z")
    )


def _require_text(
    value: str,
    name: str,
) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
    ):
        raise ValueError(
            f"{name} must not be empty"
        )

    return value.strip()