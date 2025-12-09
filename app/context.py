import json
from logging import Logger
from typing import Optional

from optum_us_ml_gen_ai_common_strands.context import AgentCoreContext
from pydantic import BaseModel
from strands.model.hooks import BeforeAgentRunHook

from app.constants import HDR_LAT , HDR_LANG , HDR_PLAN

class AgentRequestContext(BaseModel):
    lat: Optional[float] 
    lang: Optional[float] 
    plan: Optional[str] 

    @staticmethod
    def from_agent_core_context(src_ctx: AgentCoreContext) -> "AgentRequestContext":
        return AgentRequestContext(
            lat = src_ctx.get_header_values(HDR_LAT),
            lang = src_ctx.get_header_values(HDR_LANG),
            plan = src_ctx.get_header_values(HDR_PLAN)  
        )
    
    def update_event(self, event: BeforeToolCallEvent , logger: Logger):
        tool_key =event.selected_tool.spec.get("inputSchema" , {}).get("json" , {}).get("properties", {}).keys()
        tool_input = event.tool_use.get("input", {})        

        if "lat" in tool_key and self.lat is not None:
            tool_input["lat"] = self.lat

        if "lang" in tool_key and self.lang is not None:
            tool_input["lang"] = self.lang

        if "plan" in tool_key and self.plan is not None:
            tool_input["plan"] = self.plan
        
        if len(tool_input) > 0 :
            event.tool_use["input"] = tool_input
            logger.info(f"Tool input is updated. The final tool input is : {json.dumps(tool_input)}")
        else:
            logger.info(f"No parameter updated for tool input.")
