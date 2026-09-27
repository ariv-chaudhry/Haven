# __init__.py
# Haven Verification Package

# Checks that an executed plan's claimed effects actually took hold in
# the household, and recommends what to do next when they didn't. This
# is Haven's Layer 4: Action requested -> Action executed -> State
# checked -> Success or Recovery

# Modules
# verifier - verify_plan(): re-checks each successfully executed step
#            against actual household/media state
# recovery - Recommends a RecoveryAction (continue, retry, skip, ask
#            the user, or abort) for a step's execution or verification
#            outcome, and a small retry_step() helper

# Public Classes / Functions
# verify_plan            - Verifies an executed Plan's real-world effects
# VerificationResult     - The result of verifying a Plan
# VerificationStatus     - Overall outcome (VERIFIED / PARTIAL / FAILED /
#                          SKIPPED)
# StepVerification       - The verification outcome for a single step
# RecoveryAction         - What to do next about a step's outcome

from haven.verification.verifier import (
    StepVerification,
    StepVerificationStatus,
    VerificationResult,
    VerificationStatus,
    verify_plan,
)
from haven.verification.recovery import RecoveryAction

__all__ = [
    "verify_plan",
    "VerificationResult",
    "VerificationStatus",
    "StepVerification",
    "StepVerificationStatus",
    "RecoveryAction",
]
