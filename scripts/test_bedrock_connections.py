from strands import Agent
from strands.models import BedrockModel


model = BedrockModel(
    model_id="global.anthropic.claude-sonnet-4-6",
    region_name="us-west-2",
    temperature=0.2,
)

agent = Agent(
    model=model,
    system_prompt=(
        "You are a test agent. Respond exactly with: "
        "I'm Gotham's Reckoning"
    )    
)



response = agent("Confirm the connection.")

print(response)

