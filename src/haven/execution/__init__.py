# __init__.py
# Haven Execution Package

# Turns a policy-validated, structured Plan into observable changes in
# the household (or simulator today), deterministically and without any
# LLM involvement. Every step's outcome is recorded, whether it
# succeeded, failed, or was skipped

# Modules
# actions  - Deterministic handlers for each PlanStep.action, dispatched
#            by name; unsupported actions fail cleanly rather than
#            raising
# results  - ExecutionResult / StepExecutionResult contracts: execution's
#            own status lifecycle, separate from Plan/PlanStatus
# executor - The main execute_plan() entry point, which also enforces
#            that a plan awaiting confirmation is never run silently

# Public Classes / Functions
# execute_plan          - Executes every step of a Plan in order
# ExecutionResult       - The result of executing a Plan
# ExecutionStatus       - Overall outcome (COMPLETED / PARTIAL / FAILED /
#                         AWAITING_CONFIRMATION)
# StepExecutionResult   - The outcome of a single executed step

from haven.execution.executor import execute_plan
from haven.execution.results import (
    ExecutionResult,
    ExecutionStatus,
    StepExecutionResult,
    StepExecutionStatus,
)

__all__ = [
    "execute_plan",
    "ExecutionResult",
    "ExecutionStatus",
    "StepExecutionResult",
    "StepExecutionStatus",
]
