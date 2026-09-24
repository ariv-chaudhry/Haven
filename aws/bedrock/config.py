from dataclasses import dataclass
import os

@dataclass(frozen=True)
class BedrockConfig:
    region: str
    model_id: str
    temperature: float
    max_tokens: int


def load_bedrock_config() -> BedrockConfig:
    return BedrockConfig(
        region=os.getenv("AWS_REGION", "us-west-2"),
        model_id=os.getenv(
            "HAVEN_BEDROCK_MODEL_ID",
            "global.anthropic.claude-sonnet-4-6",
        ),
        temperature=float(
            os.getenv("HAVEN_BEDROCK_TEMPERATURE", "0.2")
        ),
        max_tokens=int(
            os.getenv("HAVEN_BEDROCK_MAX_TOKENS", "2048")
        ),
    )