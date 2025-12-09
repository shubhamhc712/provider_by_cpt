from typing import Any

from strands.agent.state import AgentState
from strands.hooks import HookProvider, BeforeToolCallEvent , HookRegistry

from app.context import AgentRequestContext

class RequestContextInjectingHook(HookProvider):
    "Hook to inject request context into agent message"

    def __init__(self , logger):
        self.logger = logger
    
    def before_invocation(self , event: BeforeToolCallEvent):
        "Inject request context into agent before Invocation"
        state : AgentState = event.agent.state
        ctx :   AgentRequestContext(**state.get())
        ctx.update_event(event , self.logger)
    
    def register_hooks(self, registry: HookRegistry , **kwargs:Any) -> None:
        """Register customer support memory hooks"""
        registry.add_callback(BeforeToolCallEvent , self.before_invocation)