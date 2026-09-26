"""Haven durable memory: explicit preferences and activity history.

Local/in-memory in Phase 2. Storage implementations are swappable via the
`PreferenceStore` and `ActivityStore` protocols.
"""

from haven.memory.activity import (
    ActivityRecord,
    ActivityStore,
    ActivityType,
    InMemoryActivityStore,
)
from haven.memory.preferences import (
    InMemoryPreferenceStore,
    Preference,
    PreferenceKey,
    PreferenceStore,
    is_durable_preference_key,
)
from haven.memory.service import MemoryService

__all__ = [
    "ActivityRecord",
    "ActivityStore",
    "ActivityType",
    "InMemoryActivityStore",
    "InMemoryPreferenceStore",
    "MemoryService",
    "Preference",
    "PreferenceKey",
    "PreferenceStore",
    "is_durable_preference_key",
]
