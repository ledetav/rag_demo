from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

class SummaryEngine:
    def __init__(self, api_key: str):
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3, google_api_key=api_key)

    async def update(self, old_sum: str, new_lines: list) -> str:
        prompt = (
            "Update the story summary.\n"
            f"OLD: {old_sum or 'None'}\n"
            f"NEW LINES:\n{chr(10).join(new_lines)}\n"
            "Output concise narrative summary (max 300 words)."
        )
        try:
            res = await self.llm.ainvoke([HumanMessage(content=prompt)])
            return str(res.content).strip()
        except: return old_sum