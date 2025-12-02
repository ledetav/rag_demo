from typing import Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

class SummaryEngine:
    def __init__(self, default_api_key: str):
        self.default_api_key = default_api_key

    async def update(self, old_sum: str, new_lines: list, api_key: Optional[str] = None) -> str:
        key_to_use = api_key if api_key else self.default_api_key
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3, google_api_key=key_to_use)
        
        prompt = (
            "Update the story summary.\n"
            f"OLD: {old_sum or 'None'}\n"
            f"NEW LINES:\n{chr(10).join(new_lines)}\n"
            "Output concise narrative summary (max 300 words)."
        )
        try:
            res = await llm.ainvoke([HumanMessage(content=prompt)])
            return str(res.content).strip()
        except: return old_sum