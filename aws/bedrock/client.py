"""Strands `BedrockModel` construction for Haven.

This module knows *how Haven connects to Bedrock*. It contains no planning
prompts or household logic; those live in ``haven.agents``.
"""

from __future__ import annotations

from strands.models import BedrockModel

from aws.bedrock.config import BedrockConfig


def create_bedrock_model(config: BedrockConfig) -> BedrockModel:
    """Create a Strands Bedrock model from validated configuration.

    Credentials are resolved by boto3's default credential chain; nothing is
    read from source or passed explicitly here.
    """

    return BedrockModel(
        model_id=config.model_id,
        region_name=config.region,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
    )
