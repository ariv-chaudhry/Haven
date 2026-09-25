# __init__.py
# Haven Core Package

# Contains the household domain models and the context-gathering
# subsystem that Haven's planner relies on to understand the current
# state of the home before building or executing a plan

# Modules
# models   - Domain models describing the household, its people,
#            rooms and devices, plus the shared planning contracts
# context  - The Context Resolver: gathers only the facts required
#            for the user's current goal, from approved sources,
#            asking the user directly when a fact cannot be
#            confidently obtained

# Public Classes
# Household - A single household and everything Haven knows about it
# Person    - A member of the household
# Room      - A physical room within the household
# Device    - A smart device tracked by Haven

from haven.models.household import Household
from haven.models.person import Person
from haven.models.room import Room
from haven.models.device import Device

__all__ = [
    "Household",
    "Person",
    "Room",
    "Device",
]
