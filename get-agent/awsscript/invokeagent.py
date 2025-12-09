import json
from urllib import response
import uuid

import boto3
from flask import request
from streamlit import header

client = boto3.client('bedrock-agentcore', region_name='us-east-1')

payload = json.dumps({
    "prompt": "Find provider data that can handle CPT code D2750 with latitude 41.9576904 and longitude -87.7469924"
})

event_system = client.meta.events
EVENT_NAME = 'before-sign.bedrock-agentcore.InvokeAgentRuntime'
CUSTOM_ACTOR_ID_HEADER_NAME = 'X-Amzn-Bedrock-AgentCore-Runtime-Custom-Actor-ID'
CUSTOM_ACTOR_ID_HEADER_VALUE = 'test-actor-nge-333333333333'
SESSION_ID = 'nge-3333333333333333333333333333333333333'

def add_custom_runtime_header(request, **kwargs):
    """Add custom header for agent runtime authentication/identification."""
    request.headers.add_header(CUSTOM_ACTOR_ID_HEADER_NAME, CUSTOM_ACTOR_ID_HEADER_VALUE)

handler = event_system.register_first(EVENT_NAME, add_custom_runtime_header)

response = client.invoke_agent_runtime(
    agentRuntimeArn='arn:aws:bedrock-agentcore:us-east-1:168118922028: runtime/dev_gap_exception_agent-fCQI8MCk6b',
    runtimeSessionId=SESSION_ID, # Must be 33+ chars
    payload=payload,
    traceId=f"gap-exception-{uuid.uuid4()}",
    qualifier="DEFAULT" # Optional
)

event_system.unregister(EVENT_NAME, handler)
response_body = response['response'].read()
response_list = response_body.decode().split("\n\n")

for item in response_list:
    content =item [7: len(item) - 1]
    content = content.replace('\\n', '\n')
    print(content, end="")
print("")
