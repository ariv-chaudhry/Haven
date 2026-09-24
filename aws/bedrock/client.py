from strands.models import BedrockModel

from config import BedrockConfig


def create_bedrock_model(config: BedrockConfig) -> BedrockModel:
    return BedrockModel(
        model_id=config.model_id,
        region_name=config.region,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
    )

