"""Amazon Bedrock connection configuration for Haven.

Values come from environment variables with safe defaults. Credentials are
never read here: authentication is delegated to the AWS credential chain
(``AWS_PROFILE``, SSO, instance roles, ...).
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

DEFAULT_REGION = "us-west-2"
DEFAULT_MODEL_ID = "global.anthropic.claude-sonnet-4-6"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_TOKENS = 2048

# Bedrock Converse accepts temperature in [0, 1] for the Anthropic models
# Haven targets. Values outside that range are rejected by the service.
MIN_TEMPERATURE = 0.0
MAX_TEMPERATURE = 1.0

ENV_REGION = "AWS_REGION"
ENV_REGION_FALLBACK = "AWS_DEFAULT_REGION"
ENV_MODEL_ID = "HAVEN_BEDROCK_MODEL_ID"
ENV_TEMPERATURE = "HAVEN_BEDROCK_TEMPERATURE"
ENV_MAX_TOKENS = "HAVEN_BEDROCK_MAX_TOKENS"


@dataclass(frozen=True, slots=True)
class BedrockConfig:
    """Connection settings for a Bedrock-hosted model."""

    region: str = DEFAULT_REGION
    model_id: str = DEFAULT_MODEL_ID
    temperature: float = DEFAULT_TEMPERATURE
    max_tokens: int = DEFAULT_MAX_TOKENS

    def __post_init__(self) -> None:
        if not self.region.strip():
            raise ValueError("Bedrock region must not be empty")
        if not self.model_id.strip():
            raise ValueError("Bedrock model id must not be empty")
        if not (MIN_TEMPERATURE <= self.temperature <= MAX_TEMPERATURE):
            raise ValueError(
                f"Bedrock temperature must be between {MIN_TEMPERATURE} and {MAX_TEMPERATURE}"
            )
        if self.max_tokens <= 0:
            raise ValueError("Bedrock max_tokens must be a positive integer")


def load_bedrock_config(environ: Mapping[str, str] | None = None) -> BedrockConfig:
    """Build a validated `BedrockConfig` from the environment.

    ``environ`` defaults to ``os.environ``; tests may pass a mapping.
    Raises `ValueError` for malformed or out-of-range values.
    """

    env = os.environ if environ is None else environ

    region = _text(env, ENV_REGION) or _text(env, ENV_REGION_FALLBACK) or DEFAULT_REGION
    model_id = _text(env, ENV_MODEL_ID) or DEFAULT_MODEL_ID
    temperature = _number(env, ENV_TEMPERATURE, DEFAULT_TEMPERATURE, float)
    max_tokens = _number(env, ENV_MAX_TOKENS, DEFAULT_MAX_TOKENS, int)

    return BedrockConfig(
        region=region,
        model_id=model_id,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def _text(env: Mapping[str, str], name: str) -> str:
    return (env.get(name) or "").strip()


def _number(env: Mapping[str, str], name: str, default: float, parse: type) -> float | int:
    raw = _text(env, name)
    if not raw:
        return default
    try:
        return parse(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a valid {parse.__name__}, got {raw!r}") from exc
