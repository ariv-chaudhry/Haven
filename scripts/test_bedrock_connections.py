"""Manual live smoke test: AWS credential chain -> Strands -> Bedrock.

Not part of pytest. Uses the shared Bedrock configuration and client so the
connection path matches production. Contains no Haven planning logic.

Usage:
    python scripts/test_bedrock_connections.py

Exit codes: 0 success, 1 configuration error, 2 provider/AWS error.
"""

from __future__ import annotations

import sys

from aws.bedrock.client import create_bedrock_model
from aws.bedrock.config import load_bedrock_config

EXPECTED_REPLY = "I'm Gotham's Reckoning"


def main() -> int:
    try:
        config = load_bedrock_config()
    except ValueError as exc:
        print(f"Invalid Bedrock configuration: {exc}", file=sys.stderr)
        return 1

    print(f"Region:   {config.region}")
    print(f"Model ID: {config.model_id}")

    from strands import Agent

    agent = Agent(
        model=create_bedrock_model(config),
        system_prompt=f"You are a test agent. Respond exactly with: {EXPECTED_REPLY}",
        callback_handler=None,
    )

    try:
        response = agent("Confirm the connection.")
    except Exception as exc:
        print(f"Bedrock invocation failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    text = str(response).strip()
    print(f"Response: {text}")
    if EXPECTED_REPLY not in text:
        print("Warning: response did not match the expected reply.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
