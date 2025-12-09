import logging

from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.memory.contants import StrategyType
from boto3.session import Session

boto_session = Session()
REGION = boto_session.region_name

logger = logging.getLogger(__name__)
memory_client = MemoryClient(region_name=REGION)
memory_name = "dev_gap_expection_memory"

def create_memory_resource():
    strategies = [
        {
            StrategyType.USER_PREFERENCE.value: {
                "name": "dev_gap_exception_user_preference",
                "description": "Captures customer preferences and behavior",
                "namespace": ["askai/search/gapException/{actorID}/preferences"],
                }
            },
            {
                StrategyType.SEMANTIC.value: {
                    "name": "dev_gap_exception_semantic",
                    "description": "Stores facts from conversation"
                    "namespace": ["askai/search/gapException/{actorID}/semantic"],
                }
            }        
    ]
    logger.info("Creating AgentCore Memory Resource. This can a couple of minutes...")
    # *** AGENTIC MEMORY USAGE *** - Create memory resourse and user_pref strategy
    response = memory_client.create_memory_and_wait(
        name=memory_name,
        description="Gap Exeption Memory",
        strategies=strategies,
        event_expiry_days=90, # Memory expirys in 90 days
    )
    memory_id = response["memoryId"]
    logger.info(f"Memory creation is successful. The memory ID is: {memory_id}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    create_memory_resource()