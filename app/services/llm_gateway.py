"""One safe LLM gateway for structured planning; does not persist prompts or responses."""
from __future__ import annotations
import json
import os
from time import perf_counter
from openai import OpenAI

class LLMGatewayError(RuntimeError): pass

class LLMGateway:
    def __init__(self, client_factory=OpenAI): self._client_factory=client_factory
    def configuration(self):
        return {"provider":os.getenv("MODEL_PROVIDER","DASHSCOPE"),"model":os.getenv("MODEL_NAME",os.getenv("LLM_MODEL","qwen-plus")),"configured":bool(os.getenv("DASHSCOPE_API_KEY")) and os.getenv("LLM_RUNTIME_ENABLED","false").lower()=="true"}
    def generate_plan(self, goal: str, mission_type: str, allowed_agents: list[str], allowed_tools: list[str]):
        config=self.configuration()
        if not config["configured"]: return None, {"status":"NOT_CONFIGURED","model":config["model"],"latency":0.0,"token_usage_summary":"not_called"}
        # The request is ephemeral. Only the validated plan summary is retained downstream.
        instruction=("Return JSON only with goal, agents, tools, steps, risk_points. "
          "agents must be chosen only from: "+", ".join(allowed_agents)+". tools must be chosen only from: "+", ".join(allowed_tools)+". "
          "steps must be short user-readable action labels. Do not include hidden reasoning.")
        started=perf_counter()
        try:
            client=self._client_factory(api_key=os.getenv("DASHSCOPE_API_KEY"),base_url=os.getenv("LLM_BASE_URL","https://dashscope.aliyuncs.com/compatible-mode/v1"))
            response=client.chat.completions.create(model=config["model"],messages=[{"role":"system","content":instruction},{"role":"user","content":f"Mission type: {mission_type}\nGoal: {goal}"}],response_format={"type":"json_object"})
            parsed=json.loads(response.choices[0].message.content or "{}")
            usage=getattr(response,"usage",None); total=getattr(usage,"total_tokens",None)
            return parsed,{"status":"SUCCESS","model":config["model"],"latency":round(perf_counter()-started,3),"token_usage_summary":f"total:{total}" if total is not None else "provider_not_reported"}
        except Exception as error:
            return None,{"status":"FAILED","model":config["model"],"latency":round(perf_counter()-started,3),"token_usage_summary":"not_available","error_type":type(error).__name__}
