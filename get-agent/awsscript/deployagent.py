import boto3

client = boto3.client('bedrock-agentcore-control')
response = client.create_agent_runtime(
    agentRuntimeName='dev_gap_exception_agent',
    agentRuntimeConfig={
        'containerConfiguration': {
            'containerUri' : '168118922028.dkr.ecr.us-east-1.amazonaws.com/unified-search-dev/gap-exception-agent:0.0.1-0-26d4b80a-SNAPSHOT'
        }
    }
    networkConfiguration={"networkMode": "PUBLIC"},
    roleArn='arn:aws:iam::168118922028:role/IRCustomer SupportAssistantBedrockAgentCoreRole-us-east-1',

    #authorizerConfiguration={
    #"customJWTAuthorizer": {
    #"allowedClients": [
    #"k5u2p9ts7djd6ol6ctrc8csep"]
    #"discoveryUrl": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_irJYFMnHW/.well-known/openid-configuration"
    #}
    requestHeaderConfiguration={
        "requestHeaderAllowlist": [
            # "Authorization", # Required for OAuth propagation
            "X-Amzn-Bedrock-AgentCore-Runtime-Custom-Actor-Id",
            "X-Amzn-Bedrock-AgentCore-Runtime-Custom-Location-Lat",
            "X-Amzn-Bedrock-AgentCore-Runtime-Custom-Location-Lng",
            "X-Amzn-Bedrock-AgentCore-Runtime-Custom-Location-Network-Plan",
        ]
    }
)
#Agent is: dev_gap_exception_agent-fCQI8MCk6b

print("Create Agent Runtime Response:", response)