from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

class Director:
    def __init__(self, api_key: str):
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.0, google_api_key=api_key)

    async def check_progress(self, history_text: str, goal: str) -> bool:
        if not goal: return False
        prompt = (
            f"Goal: \"{goal}\"\nChat:\n{history_text}\n"
            "Did they make significant progress towards the goal? YES or NO."
        )
        try:
            res = await self.llm.ainvoke([HumanMessage(content=prompt)])
            return "YES" in str(res.content).strip().upper()
        except: return False